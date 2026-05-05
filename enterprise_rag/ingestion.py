from __future__ import annotations

import hashlib
import re
import sqlite3
from pathlib import Path

from enterprise_rag.database import reset_documents
from enterprise_rag.retrieval import chunk_text


META_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


def parse_document(path: Path) -> tuple[dict[str, str], str]:
    raw = path.read_text(encoding="utf-8")
    match = META_RE.match(raw)
    if not match:
        raise ValueError(f"{path} must start with YAML-like metadata front matter.")
    meta_raw, body = match.groups()
    metadata: dict[str, str] = {}
    for line in meta_raw.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip()
    required = {"id", "title", "department", "allowed_roles"}
    missing = sorted(required - set(metadata))
    if missing:
        raise ValueError(f"{path} missing metadata fields: {', '.join(missing)}.")
    return metadata, body.strip()


def ingest_documents(conn: sqlite3.Connection, document_path: Path) -> dict[str, int]:
    reset_documents(conn)
    document_count = 0
    chunk_count = 0
    for path in sorted(document_path.glob("*.md")):
        metadata, body = parse_document(path)
        checksum = hashlib.sha256(path.read_bytes()).hexdigest()
        conn.execute(
            """
            INSERT INTO documents (id, title, department, allowed_roles, source_path, checksum)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                metadata["id"],
                metadata["title"],
                metadata["department"],
                metadata["allowed_roles"],
                str(path),
                checksum,
            ),
        )
        for index, chunk in enumerate(chunk_text(body)):
            chunk_id = f"{metadata['id']}:{index}"
            conn.execute(
                """
                INSERT INTO chunks (id, document_id, chunk_index, content, allowed_roles)
                VALUES (?, ?, ?, ?, ?)
                """,
                (chunk_id, metadata["id"], index, chunk, metadata["allowed_roles"]),
            )
            chunk_count += 1
        document_count += 1
    conn.commit()
    return {"documents": document_count, "chunks": chunk_count}

