from __future__ import annotations

import sqlite3

from prometheus_client import CollectorRegistry, Gauge, generate_latest

from enterprise_rag.config import Settings


_REGISTRY = CollectorRegistry(auto_describe=True)
_NS = "enterprise_rag"

documents_total = Gauge(f"{_NS}_documents_total", "Total ingested documents.", registry=_REGISTRY)
chunks_total = Gauge(f"{_NS}_chunks_total", "Total ingested chunks.", registry=_REGISTRY)
queries_total = Gauge(f"{_NS}_queries_total", "Total persisted queries.", registry=_REGISTRY)
query_latency_average_ms = Gauge(
    f"{_NS}_query_latency_average_ms",
    "Average persisted query latency in milliseconds.",
    registry=_REGISTRY,
)
restricted_leaks_total = Gauge(
    f"{_NS}_restricted_leaks_total",
    "Total restricted retrieval leaks observed in evaluation runs.",
    registry=_REGISTRY,
)
retrieval_provider_info = Gauge(
    f"{_NS}_retrieval_provider_info",
    "Active retrieval provider.",
    ["provider"],
    registry=_REGISTRY,
)


def prometheus_metrics(conn: sqlite3.Connection, settings: Settings) -> str:
    document_count = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    chunk_count = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    query_count = conn.execute("SELECT COUNT(*) FROM query_logs").fetchone()[0]
    average_latency_ms = conn.execute("SELECT COALESCE(AVG(latency_ms), 0) FROM query_logs").fetchone()[0]
    restricted_leaks = conn.execute(
        "SELECT COALESCE(SUM(restricted_leak_count), 0) FROM evaluation_runs"
    ).fetchone()[0]

    documents_total.set(float(document_count))
    chunks_total.set(float(chunk_count))
    queries_total.set(float(query_count))
    query_latency_average_ms.set(float(average_latency_ms))
    restricted_leaks_total.set(float(restricted_leaks))
    retrieval_provider_info.labels(provider=settings.retrieval_provider).set(1)

    return generate_latest(_REGISTRY).decode("utf-8")
