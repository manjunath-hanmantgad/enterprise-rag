from __future__ import annotations

import httpx

from enterprise_rag.config import Settings
from enterprise_rag.retrieval import RetrievedChunk


class AnswerGenerator:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.settings.require_provider_credentials()

    def answer(self, question: str, chunks: list[RetrievedChunk]) -> str:
        if not chunks:
            return (
                "I could not find enough accessible source material to answer this question. "
                "Ask an administrator to confirm document access or ingest more relevant sources."
            )
        provider = self.settings.llm_provider.lower()
        if provider == "openai":
            return self._openai_answer(question, chunks)
        if provider == "azure":
            return self._azure_openai_answer(question, chunks)
        facts = []
        for chunk in chunks[:3]:
            first_sentence = chunk.content.split(".")[0].strip()
            if first_sentence:
                facts.append(f"{first_sentence}.")
        return " ".join(facts) + " See the citations for the source documents used."

    def _messages(self, question: str, chunks: list[RetrievedChunk]) -> list[dict]:
        context = "\n\n".join(
            f"[{index + 1}] {chunk.title} ({chunk.document_id})\n{chunk.content}" for index, chunk in enumerate(chunks)
        )
        return [
            {
                "role": "system",
                "content": (
                    "You answer internal company knowledge questions. Use only the provided context. "
                    "If the context is insufficient, say so. Include citation markers like [1] when using a source."
                ),
            },
            {"role": "user", "content": f"Question: {question}\n\nContext:\n{context}"},
        ]

    def _extract_answer(self, response: httpx.Response) -> str:
        response.raise_for_status()
        body = response.json()
        try:
            return body["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("LLM provider returned an unexpected response shape.") from exc

    def _openai_answer(self, question: str, chunks: list[RetrievedChunk]) -> str:
        response = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.settings.openai_model,
                "messages": self._messages(question, chunks),
                "temperature": 0,
            },
            timeout=30,
        )
        return self._extract_answer(response)

    def _azure_openai_answer(self, question: str, chunks: list[RetrievedChunk]) -> str:
        endpoint = self.settings.azure_openai_endpoint.rstrip("/")
        deployment = self.settings.azure_openai_chat_deployment
        url = (
            f"{endpoint}/openai/deployments/{deployment}/chat/completions"
            f"?api-version={self.settings.azure_openai_api_version}"
        )
        response = httpx.post(
            url,
            headers={"api-key": self.settings.azure_openai_key, "Content-Type": "application/json"},
            json={"messages": self._messages(question, chunks), "temperature": 0},
            timeout=30,
        )
        return self._extract_answer(response)
