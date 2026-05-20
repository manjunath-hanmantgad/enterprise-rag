#!/usr/bin/env python3
"""Eval runner for Enterprise RAG."""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from enterprise_rag import auth
from enterprise_rag.retrieval import cosine_score, role_allowed
from enterprise_rag.service import answer_question


class MockSettings:
    llm_provider = "mock"
    retrieval_provider = "local"
    openai_model = "gpt-4o-mini"
    openai_api_key = ""
    azure_openai_endpoint = ""
    azure_openai_key = ""
    azure_openai_chat_deployment = ""
    azure_openai_api_version = "2024-10-21"

    def require_provider_credentials(self) -> None:
        return None

    def require_retrieval_credentials(self) -> None:
        return None


def run_retrieval(case: dict) -> tuple[bool, str]:
    payload = case["input"]
    expected = case["expected"]
    query = payload["query"]
    top_k = int(payload.get("top_k", 4))

    scored: list[tuple[str, float]] = []
    for candidate in payload["candidates"]:
        score = cosine_score(query, candidate["content"])
        if score > 0:
            scored.append((candidate["document_id"], score))
    scored.sort(key=lambda item: item[1], reverse=True)
    returned_ids = [item[0] for item in scored[:top_k]]

    expected_ids = set(expected.get("expected_document_ids", []))
    returned_set = set(returned_ids)
    intersection = len(returned_set & expected_ids)

    precision = intersection / len(returned_ids) if returned_ids else 1.0
    recall = intersection / len(expected_ids) if expected_ids else 1.0

    passed = precision >= float(expected.get("min_precision", 0.0)) and recall >= float(expected.get("min_recall", 0.0))
    detail = f"returned={returned_ids} precision={precision:.2f} recall={recall:.2f}"
    return passed, detail


def run_access(case: dict) -> tuple[bool, str]:
    payload = case["input"]
    expected = case["expected"]
    user_role = payload["user_role"]
    allowed_roles = payload["allowed_roles"]

    role_valid = user_role in auth.VALID_ROLES
    granted = role_allowed(user_role, allowed_roles)

    passed = role_valid == bool(expected["role_valid"]) and granted == bool(expected["access_granted"])
    detail = f"role_valid={role_valid} granted={granted}"
    return passed, detail


def _build_citation_db(payload: dict) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE documents (id TEXT PRIMARY KEY, title TEXT NOT NULL)")
    conn.execute(
        "CREATE TABLE chunks (id TEXT PRIMARY KEY, document_id TEXT NOT NULL, content TEXT NOT NULL, allowed_roles TEXT NOT NULL)"
    )

    for doc in payload["documents"]:
        conn.execute("INSERT INTO documents (id, title) VALUES (?, ?)", (doc["id"], doc["title"]))
    for chunk in payload["chunks"]:
        conn.execute(
            "INSERT INTO chunks (id, document_id, content, allowed_roles) VALUES (?, ?, ?, ?)",
            (chunk["chunk_id"], chunk["document_id"], chunk["content"], chunk["allowed_roles"]),
        )
    conn.commit()
    return conn


def run_citation(case: dict) -> tuple[bool, str]:
    payload = case["input"]
    expected = case["expected"]

    conn = _build_citation_db(payload)
    try:
        response = answer_question(
            conn,
            MockSettings(),
            payload["question"],
            payload["user_role"],
            int(payload.get("top_k", 4)),
            persist=False,
        )
    finally:
        conn.close()

    returned = {citation.document_id for citation in response.citations}
    expected_ids = set(expected.get("expected_document_ids", []))
    forbidden = set(expected.get("forbidden_document_ids", []))

    passed = expected_ids.issubset(returned) and not bool(returned & forbidden)
    detail = f"returned={sorted(returned)} expected={sorted(expected_ids)} forbidden={sorted(forbidden)}"
    return passed, detail


def main() -> int:
    dataset_path = Path(__file__).with_name("golden_dataset.json")
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))

    runners = {
        "retrieval": run_retrieval,
        "access_control": run_access,
        "citation": run_citation,
    }

    executed = 0
    passed = 0
    skipped = 0
    failures: list[tuple[str, str]] = []

    for case in dataset["cases"]:
        case_id = case["id"]
        if case.get("requires_live_llm", False):
            skipped += 1
            print(f"[SKIP] {case_id} requires live LLM")
            continue

        runner = runners.get(case["category"])
        if runner is None:
            executed += 1
            failures.append((case_id, f"unsupported category: {case['category']}"))
            print(f"[FAIL] {case_id} unsupported category")
            continue

        ok, detail = runner(case)
        executed += 1
        if ok:
            passed += 1
            print(f"[PASS] {case_id} {detail}")
        else:
            failures.append((case_id, detail))
            print(f"[FAIL] {case_id} {detail}")

    print("\nSummary")
    print(f"Executed: {executed}")
    print(f"Passed:   {passed}")
    print(f"Skipped:  {skipped}")
    print(f"Failed:   {len(failures)}")

    if failures:
        print("\nFailed cases:")
        for case_id, detail in failures:
            print(f"- {case_id}: {detail}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
