from __future__ import annotations

import json
import sqlite3
from typing import Any


def write_audit_log(conn: sqlite3.Connection, action: str, actor: str, detail: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO audit_logs (action, actor, detail)
        VALUES (?, ?, ?)
        """,
        (action, actor, json.dumps(detail, sort_keys=True)),
    )
    conn.commit()


def list_audit_logs(conn: sqlite3.Connection, limit: int = 100) -> list[dict]:
    rows = conn.execute(
        """
        SELECT id, action, actor, detail, created_at
        FROM audit_logs
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]

