from __future__ import annotations

import sqlite3

from enterprise_rag.config import Settings


def prometheus_metrics(conn: sqlite3.Connection, settings: Settings) -> str:
    document_count = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    chunk_count = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    query_count = conn.execute("SELECT COUNT(*) FROM query_logs").fetchone()[0]
    average_latency_ms = conn.execute("SELECT COALESCE(AVG(latency_ms), 0) FROM query_logs").fetchone()[0]
    restricted_leaks = conn.execute(
        "SELECT COALESCE(SUM(restricted_leak_count), 0) FROM evaluation_runs"
    ).fetchone()[0]
    lines = [
        "# HELP enterprise_rag_documents_total Total ingested documents.",
        "# TYPE enterprise_rag_documents_total gauge",
        f"enterprise_rag_documents_total {document_count}",
        "# HELP enterprise_rag_chunks_total Total ingested chunks.",
        "# TYPE enterprise_rag_chunks_total gauge",
        f"enterprise_rag_chunks_total {chunk_count}",
        "# HELP enterprise_rag_queries_total Total persisted queries.",
        "# TYPE enterprise_rag_queries_total counter",
        f"enterprise_rag_queries_total {query_count}",
        "# HELP enterprise_rag_query_latency_average_ms Average persisted query latency in milliseconds.",
        "# TYPE enterprise_rag_query_latency_average_ms gauge",
        f"enterprise_rag_query_latency_average_ms {float(average_latency_ms):.2f}",
        "# HELP enterprise_rag_restricted_leaks_total Total restricted retrieval leaks observed in evaluation runs.",
        "# TYPE enterprise_rag_restricted_leaks_total counter",
        f"enterprise_rag_restricted_leaks_total {restricted_leaks}",
        "# HELP enterprise_rag_retrieval_provider_info Active retrieval provider.",
        "# TYPE enterprise_rag_retrieval_provider_info gauge",
        f'enterprise_rag_retrieval_provider_info{{provider="{settings.retrieval_provider}"}} 1',
    ]
    return "\n".join(lines) + "\n"
