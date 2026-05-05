from __future__ import annotations

from dataclasses import dataclass
import sqlite3
from typing import Protocol

import httpx

from enterprise_rag.config import Settings
from enterprise_rag.retrieval import RetrievedChunk, cosine_score, role_allowed


@dataclass
class RetrievalResult:
    chunks: list[RetrievedChunk]
    blocked_count: int
    provider: str


class Retriever(Protocol):
    provider_name: str

    def search(self, conn: sqlite3.Connection, question: str, user_role: str, top_k: int) -> RetrievalResult:
        ...


class LocalLexicalRetriever:
    provider_name = "local"

    def search(self, conn: sqlite3.Connection, question: str, user_role: str, top_k: int) -> RetrievalResult:
        rows = conn.execute(
            """
            SELECT chunks.id AS chunk_id, chunks.document_id, documents.title, chunks.content, chunks.allowed_roles
            FROM chunks
            JOIN documents ON documents.id = chunks.document_id
            """
        ).fetchall()
        scored: list[RetrievedChunk] = []
        blocked_count = 0
        for row in rows:
            allowed_roles = [role.strip() for role in row["allowed_roles"].split(",") if role.strip()]
            if not role_allowed(user_role, allowed_roles):
                blocked_count += 1
                continue
            score = cosine_score(question, row["content"])
            if score > 0:
                scored.append(
                    RetrievedChunk(
                        chunk_id=row["chunk_id"],
                        document_id=row["document_id"],
                        title=row["title"],
                        content=row["content"],
                        score=round(score, 4),
                        allowed_roles=allowed_roles,
                    )
                )
        scored.sort(key=lambda chunk: chunk.score, reverse=True)
        return RetrievalResult(chunks=scored[:top_k], blocked_count=blocked_count, provider=self.provider_name)


class OpenAIVectorRetriever:
    provider_name = "openai"

    def __init__(self, settings: Settings):
        self.settings = settings

    def search(self, conn: sqlite3.Connection, question: str, user_role: str, top_k: int) -> RetrievalResult:
        del conn, question, user_role, top_k
        self.settings.require_retrieval_credentials()
        raise RuntimeError("OpenAI vector retrieval is not implemented yet.")


class AzureAISearchRetriever:
    provider_name = "azure_ai_search"

    def __init__(self, settings: Settings):
        self.settings = settings

    def search(self, conn: sqlite3.Connection, question: str, user_role: str, top_k: int) -> RetrievalResult:
        del conn
        self.settings.require_retrieval_credentials()
        endpoint = self.settings.azure_ai_search_endpoint.rstrip("/")
        url = f"{endpoint}/indexes/{self.settings.azure_ai_search_index}/docs/search?api-version=2024-07-01"
        response = httpx.post(
            url,
            headers={"api-key": self.settings.azure_ai_search_key, "Content-Type": "application/json"},
            json={
                "search": question,
                "top": top_k,
                "filter": f"allowed_roles/any(role: role eq 'all' or role eq '{user_role}')",
                "select": "chunk_id,document_id,title,content,allowed_roles",
            },
            timeout=30,
        )
        response.raise_for_status()
        chunks: list[RetrievedChunk] = []
        for item in response.json().get("value", []):
            allowed_roles = item.get("allowed_roles") or []
            if isinstance(allowed_roles, str):
                allowed_roles = [role.strip() for role in allowed_roles.split(",") if role.strip()]
            chunks.append(
                RetrievedChunk(
                    chunk_id=item.get("chunk_id") or item.get("id") or "",
                    document_id=item.get("document_id") or "",
                    title=item.get("title") or item.get("document_id") or "Untitled",
                    content=item.get("content") or "",
                    score=round(float(item.get("@search.score", 0)), 4),
                    allowed_roles=allowed_roles,
                )
            )
        return RetrievalResult(chunks=chunks, blocked_count=0, provider=self.provider_name)


def get_retriever(settings: Settings) -> Retriever:
    provider = settings.retrieval_provider.lower()
    if provider == "local":
        return LocalLexicalRetriever()
    if provider == "openai":
        settings.require_retrieval_credentials()
        return OpenAIVectorRetriever(settings)
    if provider == "azure_ai_search":
        settings.require_retrieval_credentials()
        return AzureAISearchRetriever(settings)
    settings.require_retrieval_credentials()
    raise RuntimeError("unreachable retrieval provider")
