from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from enterprise_rag.config import Settings
from enterprise_rag.service import answer_question


def run_evaluation(conn: sqlite3.Connection, settings: Settings, eval_set_path: Path) -> dict:
    cases = json.loads(eval_set_path.read_text(encoding="utf-8"))
    pass_count = 0
    restricted_leak_count = 0
    citation_total = 0
    latency_total = 0
    results = []
    for case in cases:
        response = answer_question(
            conn,
            settings,
            case["question"],
            case["user_role"],
            top_k=4,
            persist=False,
        )
        returned_docs = {citation.document_id for citation in response.citations}
        expected_docs = set(case.get("expected_document_ids", []))
        forbidden_docs = set(case.get("forbidden_document_ids", []))
        leaked = bool(returned_docs & forbidden_docs)
        passed = expected_docs.issubset(returned_docs) and not leaked
        pass_count += int(passed)
        restricted_leak_count += int(leaked)
        citation_total += len(response.citations)
        latency_total += response.latency_ms
        results.append(
            {
                "name": case["name"],
                "passed": passed,
                "returned_document_ids": sorted(returned_docs),
                "expected_document_ids": sorted(expected_docs),
                "forbidden_document_ids": sorted(forbidden_docs),
                "latency_ms": response.latency_ms,
            }
        )
    total = len(cases)
    citation_coverage = citation_total / total if total else 0
    average_latency_ms = latency_total / total if total else 0
    summary = {
        "total_cases": total,
        "pass_count": pass_count,
        "pass_rate": round(pass_count / total, 3) if total else 0,
        "restricted_leak_count": restricted_leak_count,
        "citation_coverage": round(citation_coverage, 3),
        "average_latency_ms": round(average_latency_ms, 2),
        "results": results,
    }
    conn.execute(
        """
        INSERT INTO evaluation_runs
        (total_cases, pass_count, restricted_leak_count, citation_coverage, average_latency_ms)
        VALUES (?, ?, ?, ?, ?)
        """,
        (total, pass_count, restricted_leak_count, citation_coverage, average_latency_ms),
    )
    conn.commit()
    return summary

