from __future__ import annotations

import json
import sqlite3
import time

from enterprise_rag.config import Settings
from enterprise_rag.llm import AnswerGenerator
from enterprise_rag.retrievers import get_retriever
from enterprise_rag.schemas import Citation, QueryResponse


def answer_question(
    conn: sqlite3.Connection,
    settings: Settings,
    question: str,
    user_role: str,
    top_k: int,
    persist: bool = True,
) -> QueryResponse:
    start = time.perf_counter()
    retrieval = get_retriever(settings).search(conn, question, user_role, top_k)
    chunks = retrieval.chunks
    blocked_count = retrieval.blocked_count
    answer = AnswerGenerator(settings).answer(question, chunks)
    latency_ms = int((time.perf_counter() - start) * 1000)
    citations = [
        Citation(
            document_id=chunk.document_id,
            title=chunk.title,
            chunk_id=chunk.chunk_id,
            excerpt=chunk.content[:280],
            score=chunk.score,
        )
        for chunk in chunks
    ]
    metrics = {
        "retrieved_count": len(chunks),
        "blocked_count": blocked_count,
        "citation_count": len(citations),
        "top_score": citations[0].score if citations else 0,
        "retrieval_provider": retrieval.provider,
    }
    if persist:
        conn.execute(
            """
            INSERT INTO query_logs
            (question, user_role, answer, citations_json, latency_ms, retrieved_count, blocked_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                question,
                user_role,
                answer,
                json.dumps([citation.model_dump() for citation in citations]),
                latency_ms,
                len(chunks),
                blocked_count,
            ),
        )
        conn.commit()
    return QueryResponse(
        answer=answer,
        citations=citations,
        user_role=user_role,
        latency_ms=latency_ms,
        metrics=metrics,
    )
