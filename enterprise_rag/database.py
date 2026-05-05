from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Iterable, Sequence


SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    department TEXT NOT NULL,
    allowed_roles TEXT NOT NULL,
    source_path TEXT NOT NULL,
    checksum TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    allowed_roles TEXT NOT NULL,
    FOREIGN KEY(document_id) REFERENCES documents(id)
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS api_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    key_prefix TEXT NOT NULL,
    key_hash TEXT NOT NULL UNIQUE,
    revoked_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS query_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT NOT NULL,
    user_role TEXT NOT NULL,
    answer TEXT NOT NULL,
    citations_json TEXT NOT NULL,
    latency_ms INTEGER NOT NULL,
    retrieved_count INTEGER NOT NULL,
    blocked_count INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS evaluation_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    total_cases INTEGER NOT NULL,
    pass_count INTEGER NOT NULL,
    restricted_leak_count INTEGER NOT NULL,
    citation_coverage REAL NOT NULL,
    average_latency_ms REAL NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,
    actor TEXT NOT NULL,
    detail TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

POSTGRES_SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    department TEXT NOT NULL,
    allowed_roles TEXT NOT NULL,
    source_path TEXT NOT NULL,
    checksum TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents(id),
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    allowed_roles TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS api_keys (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id),
    name TEXT NOT NULL,
    key_prefix TEXT NOT NULL,
    key_hash TEXT NOT NULL UNIQUE,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS query_logs (
    id BIGSERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    user_role TEXT NOT NULL,
    answer TEXT NOT NULL,
    citations_json TEXT NOT NULL,
    latency_ms INTEGER NOT NULL,
    retrieved_count INTEGER NOT NULL,
    blocked_count INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS evaluation_runs (
    id BIGSERIAL PRIMARY KEY,
    total_cases INTEGER NOT NULL,
    pass_count INTEGER NOT NULL,
    restricted_leak_count INTEGER NOT NULL,
    citation_coverage DOUBLE PRECISION NOT NULL,
    average_latency_ms DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGSERIAL PRIMARY KEY,
    action TEXT NOT NULL,
    actor TEXT NOT NULL,
    detail TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


class CompatRow(dict):
    def __init__(self, values: dict[str, Any]):
        super().__init__(values)
        self._values = tuple(values.values())

    def __getitem__(self, key: str | int) -> Any:
        if isinstance(key, int):
            return self._values[key]
        return super().__getitem__(key)


class PostgresCursor:
    def __init__(self, cursor: Any):
        self.cursor = cursor

    @property
    def rowcount(self) -> int:
        return self.cursor.rowcount

    def fetchone(self) -> CompatRow | None:
        row = self.cursor.fetchone()
        return CompatRow(row) if row is not None else None

    def fetchall(self) -> list[CompatRow]:
        return [CompatRow(row) for row in self.cursor.fetchall()]


class PostgresConnection:
    backend = "postgres"

    def __init__(self, raw_conn: Any):
        self.raw_conn = raw_conn

    def execute(self, sql: str, params: Sequence[Any] | None = None) -> PostgresCursor:
        cursor = self.raw_conn.cursor()
        cursor.execute(_translate_placeholders(sql), tuple(params or ()))
        return PostgresCursor(cursor)

    def executescript(self, script: str) -> None:
        for statement in _split_sql_script(script):
            self.execute(statement)

    def commit(self) -> None:
        self.raw_conn.commit()

    def rollback(self) -> None:
        self.raw_conn.rollback()

    def close(self) -> None:
        self.raw_conn.close()

    def __enter__(self) -> "PostgresConnection":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.close()


def _translate_placeholders(sql: str) -> str:
    return sql.replace("?", "%s")


def _split_sql_script(script: str) -> list[str]:
    return [statement.strip() for statement in script.split(";") if statement.strip()]


def connect(database_path: Path) -> sqlite3.Connection:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    return conn


def connect_from_settings(settings: Any) -> sqlite3.Connection | PostgresConnection:
    if settings.storage_backend == "sqlite":
        return connect(settings.database_path)
    if settings.storage_backend in {"postgres", "azure_postgres"}:
        if not settings.database_url:
            raise RuntimeError(f"STORAGE_BACKEND={settings.storage_backend} requires DATABASE_URL.")
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError(
                "PostgreSQL storage requires psycopg. Install dependencies from requirements.txt before enabling "
                f"STORAGE_BACKEND={settings.storage_backend}."
            ) from exc
        return PostgresConnection(psycopg.connect(settings.database_url, row_factory=dict_row))
    raise RuntimeError("STORAGE_BACKEND must be one of: sqlite, postgres, azure_postgres.")


def init_db(conn: Any) -> None:
    schema = POSTGRES_SCHEMA if isinstance(conn, PostgresConnection) else SQLITE_SCHEMA
    conn.executescript(schema)
    conn.commit()


def reset_documents(conn: Any) -> None:
    conn.execute("DELETE FROM chunks")
    conn.execute("DELETE FROM documents")
    conn.commit()


def rows_to_dicts(rows: Iterable[Any]) -> list[dict]:
    return [dict(row) for row in rows]


def is_integrity_error(exc: Exception) -> bool:
    if isinstance(exc, sqlite3.IntegrityError):
        return True
    return exc.__class__.__name__ in {"IntegrityError", "UniqueViolation", "ForeignKeyViolation"}
