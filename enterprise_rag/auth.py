from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status

from enterprise_rag.database import is_integrity_error
from enterprise_rag.security import generate_api_key, hash_api_key, hash_secret


VALID_ROLES = {"employee", "engineer", "finance", "admin"}


def create_user(conn: Any, username: str, full_name: str, role: str, password: str) -> dict:
    normalized_role = role.strip().lower()
    if normalized_role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"role must be one of: {', '.join(sorted(VALID_ROLES))}")
    try:
        cursor = conn.execute(
            """
            INSERT INTO users (username, full_name, role, password_hash)
            VALUES (?, ?, ?, ?)
            RETURNING id
            """,
            (username.strip().lower(), full_name.strip(), normalized_role, hash_secret(password)),
        )
        row = cursor.fetchone()
        conn.commit()
    except Exception as exc:
        if is_integrity_error(exc):
            raise HTTPException(status_code=409, detail="username already exists") from exc
        raise
    return {
        "id": row["id"],
        "username": username.strip().lower(),
        "full_name": full_name.strip(),
        "role": normalized_role,
    }


def create_api_key(conn: Any, username: str, name: str) -> dict:
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username.strip().lower(),)).fetchone()
    if not user:
        raise HTTPException(status_code=404, detail="user not found")
    api_key = generate_api_key()
    cursor = conn.execute(
        """
        INSERT INTO api_keys (user_id, name, key_prefix, key_hash)
        VALUES (?, ?, ?, ?)
        RETURNING id
        """,
        (user["id"], name.strip(), api_key[:12], hash_api_key(api_key)),
    )
    row = cursor.fetchone()
    conn.commit()
    return {
        "id": row["id"],
        "name": name.strip(),
        "key_prefix": api_key[:12],
        "api_key": api_key,
        "username": user["username"],
        "role": user["role"],
    }


def list_api_keys(conn: Any) -> list[dict]:
    rows = conn.execute(
        """
        SELECT api_keys.id, api_keys.name, api_keys.key_prefix, api_keys.revoked_at, api_keys.created_at,
               users.username, users.full_name, users.role
        FROM api_keys
        JOIN users ON users.id = api_keys.user_id
        ORDER BY api_keys.id DESC
        """
    ).fetchall()
    return [dict(row) for row in rows]


def revoke_api_key(conn: Any, api_key_id: int) -> dict:
    cursor = conn.execute(
        "UPDATE api_keys SET revoked_at = CURRENT_TIMESTAMP WHERE id = ? AND revoked_at IS NULL",
        (api_key_id,),
    )
    conn.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="active API key not found")
    return {"id": api_key_id, "revoked": True}


def get_api_key_context(conn: Any, api_key: str) -> dict:
    row = conn.execute(
        """
        SELECT users.username, users.full_name, users.role, api_keys.id AS api_key_id, api_keys.name AS api_key_name
        FROM api_keys
        JOIN users ON users.id = api_keys.user_id
        WHERE api_keys.key_hash = ? AND api_keys.revoked_at IS NULL
        """,
        (hash_api_key(api_key),),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid or revoked API key")
    return dict(row)


def seed_reference_users(conn: Any) -> None:
    reference_users = [
        ("emma.employee", "Emma Employee", "employee"),
        ("eric.engineer", "Eric Engineer", "engineer"),
        ("fatima.finance", "Fatima Finance", "finance"),
        ("ava.admin", "Ava Admin", "admin"),
    ]
    for username, full_name, role in reference_users:
        exists = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if not exists:
            create_user(conn, username, full_name, role, "change-me-local-password")
