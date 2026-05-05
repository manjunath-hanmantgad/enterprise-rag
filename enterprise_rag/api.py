from __future__ import annotations

from typing import Annotated
import time
import uuid

from fastapi import FastAPI, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

from enterprise_rag.auth import create_api_key, create_user, get_api_key_context, list_api_keys, revoke_api_key, seed_reference_users
from enterprise_rag.audit import list_audit_logs, write_audit_log
from enterprise_rag.config import get_settings
from enterprise_rag.database import connect_from_settings, init_db, rows_to_dicts
from enterprise_rag.evaluation import run_evaluation
from enterprise_rag.ingestion import ingest_documents
from enterprise_rag.logging_config import configure_logging
from enterprise_rag.metrics import prometheus_metrics
from enterprise_rag.oidc import validate_bearer_token
from enterprise_rag.rate_limit import allow_request, rate_limit_key
from enterprise_rag.schemas import (
    AuditLogRead,
    ApiKeyCreate,
    ApiKeyCreateResponse,
    ApiKeyRead,
    DocumentRead,
    IngestResponse,
    MetricsResponse,
    QueryLogRead,
    QueryRequest,
    QueryResponse,
    UserCreate,
    UserRead,
)
from enterprise_rag.service import answer_question


settings = get_settings()
logger = configure_logging(settings.json_logs)

app = FastAPI(
    title="Enterprise RAG",
    description="Secure local-first document QA with citations, access control, and retrieval evaluation.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Admin-Token", "X-API-Key", "X-Request-ID"],
)


@app.middleware("http")
async def operational_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    start = time.perf_counter()
    current_settings = get_settings()
    if request.url.path not in {"/health", "/ready", "/metrics", "/metrics/prometheus"}:
        client_host = request.client.host if request.client else "unknown"
        key = rate_limit_key(
            str(current_settings.database_path),
            client_host,
            request.headers.get("X-API-Key"),
        )
        allowed, remaining = allow_request(key, current_settings.rate_limit_per_minute)
        if not allowed:
            response = JSONResponse(
                status_code=429,
                content={"detail": "rate limit exceeded", "request_id": request_id},
                headers={"X-Request-ID": request_id, "X-RateLimit-Remaining": "0"},
            )
            return response
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    if request.url.path not in {"/health", "/ready", "/metrics", "/metrics/prometheus"}:
        response.headers["X-RateLimit-Remaining"] = str(remaining)
    if settings.security_headers_enabled:
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    latency_ms = int((time.perf_counter() - start) * 1000)
    logger.info(
        "request completed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "latency_ms": latency_ms,
        },
    )
    return response


@app.exception_handler(RuntimeError)
async def runtime_error_handler(request: Request, exc: RuntimeError):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    message = str(exc)
    status_code = 503 if "requires" in message or "missing" in message or "not implemented" in message else 500
    return JSONResponse(
        status_code=status_code,
        content={"detail": message, "request_id": request_id},
        headers={"X-Request-ID": request_id},
    )


def get_conn():
    settings = get_settings()
    conn = connect_from_settings(settings)
    init_db(conn)
    return conn


def require_admin_token(settings, x_admin_token: str | None) -> str:
    if not settings.admin_token:
        return "local-admin"
    if x_admin_token != settings.admin_token:
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="admin token required")
    return "admin-token"


@app.get("/health")
def health() -> dict[str, str]:
    settings = get_settings()
    settings.require_provider_credentials()
    settings.require_retrieval_credentials()
    settings.require_storage_credentials()
    settings.require_auth_provider()
    return {
        "status": "ok",
        "llm_provider": settings.llm_provider,
        "retrieval_provider": settings.retrieval_provider,
        "storage_backend": settings.storage_backend,
        "auth_provider": settings.auth_provider,
    }


@app.get("/ready")
def ready() -> dict[str, str | int]:
    settings = get_settings()
    settings.require_provider_credentials()
    settings.require_retrieval_credentials()
    settings.require_storage_credentials()
    settings.require_auth_provider()
    with get_conn() as conn:
        conn.execute("SELECT 1").fetchone()
        document_count = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    return {
        "status": "ready",
        "database": "ok",
        "document_count": document_count,
        "llm_provider": settings.llm_provider,
        "retrieval_provider": settings.retrieval_provider,
    }


@app.post("/ingest", response_model=IngestResponse)
def ingest(x_admin_token: Annotated[str | None, Header(alias="X-Admin-Token")] = None) -> dict[str, int]:
    settings = get_settings()
    actor = require_admin_token(settings, x_admin_token)
    with get_conn() as conn:
        seed_reference_users(conn)
        result = ingest_documents(conn, settings.document_path)
        write_audit_log(conn, "documents.ingest", actor, result)
        return result


@app.post("/auth/register", response_model=UserRead)
def register(request: UserCreate, x_admin_token: Annotated[str | None, Header(alias="X-Admin-Token")] = None) -> dict:
    settings = get_settings()
    actor = require_admin_token(settings, x_admin_token)
    with get_conn() as conn:
        user = create_user(conn, request.username, request.full_name, request.role, request.password)
        write_audit_log(conn, "users.create", actor, {"username": user["username"], "role": user["role"]})
        return user


@app.post("/api-keys", response_model=ApiKeyCreateResponse)
def create_key(request: ApiKeyCreate, x_admin_token: Annotated[str | None, Header(alias="X-Admin-Token")] = None) -> dict:
    settings = get_settings()
    actor = require_admin_token(settings, x_admin_token)
    with get_conn() as conn:
        api_key = create_api_key(conn, request.username, request.name)
        write_audit_log(conn, "api_keys.create", actor, {"username": api_key["username"], "key_prefix": api_key["key_prefix"]})
        return api_key


@app.get("/api-keys", response_model=list[ApiKeyRead])
def api_keys(x_admin_token: Annotated[str | None, Header(alias="X-Admin-Token")] = None) -> list[dict]:
    settings = get_settings()
    require_admin_token(settings, x_admin_token)
    with get_conn() as conn:
        return list_api_keys(conn)


@app.post("/api-keys/{api_key_id}/revoke")
def revoke_key(api_key_id: int, x_admin_token: Annotated[str | None, Header(alias="X-Admin-Token")] = None) -> dict:
    settings = get_settings()
    actor = require_admin_token(settings, x_admin_token)
    with get_conn() as conn:
        result = revoke_api_key(conn, api_key_id)
        write_audit_log(conn, "api_keys.revoke", actor, {"api_key_id": api_key_id})
        return result


@app.get("/audit-logs", response_model=list[AuditLogRead])
def audit_logs(
    x_admin_token: Annotated[str | None, Header(alias="X-Admin-Token")] = None,
    limit: int = 100,
) -> list[dict]:
    settings = get_settings()
    require_admin_token(settings, x_admin_token)
    with get_conn() as conn:
        return list_audit_logs(conn, limit=limit)


@app.get("/documents", response_model=list[DocumentRead])
def documents() -> list[dict]:
    with get_conn() as conn:
        rows = rows_to_dicts(conn.execute("SELECT * FROM documents ORDER BY title").fetchall())
    for row in rows:
        row["allowed_roles"] = [role.strip() for role in row["allowed_roles"].split(",") if role.strip()]
    return rows


@app.get("/query-logs", response_model=list[QueryLogRead])
def query_logs(limit: int = 20) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, question, user_role, retrieved_count, blocked_count, latency_ms, created_at
            FROM query_logs
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return rows_to_dicts(rows)


@app.post("/query", response_model=QueryResponse)
def query(
    request: QueryRequest,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> QueryResponse:
    settings = get_settings()
    with get_conn() as conn:
        user_role = request.user_role
        if x_api_key:
            context = get_api_key_context(conn, x_api_key)
            user_role = context["role"]
        elif settings.auth_provider != "local" and authorization:
            scheme, _, token = authorization.partition(" ")
            if scheme.lower() != "bearer" or not token:
                from fastapi import HTTPException

                raise HTTPException(status_code=401, detail="Bearer token required")
            context = validate_bearer_token(token, settings)
            user_role = context["role"]
        return answer_question(conn, settings, request.question, user_role, request.top_k)


@app.post("/eval/run")
def evaluate(x_admin_token: Annotated[str | None, Header(alias="X-Admin-Token")] = None) -> dict:
    settings = get_settings()
    actor = require_admin_token(settings, x_admin_token)
    with get_conn() as conn:
        result = run_evaluation(conn, settings, settings.eval_set_path)
        write_audit_log(
            conn,
            "evaluations.run",
            actor,
            {"total_cases": result["total_cases"], "pass_count": result["pass_count"]},
        )
        return result


@app.get("/metrics", response_model=MetricsResponse)
def metrics() -> dict:
    with get_conn() as conn:
        document_count = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        chunk_count = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        query_count = conn.execute("SELECT COUNT(*) FROM query_logs").fetchone()[0]
        average_latency_ms = conn.execute("SELECT COALESCE(AVG(latency_ms), 0) FROM query_logs").fetchone()[0]
        last_eval = conn.execute("SELECT * FROM evaluation_runs ORDER BY id DESC LIMIT 1").fetchone()
    return {
        "document_count": document_count,
        "chunk_count": chunk_count,
        "query_count": query_count,
        "average_latency_ms": round(float(average_latency_ms), 2),
        "retrieval_provider": get_settings().retrieval_provider,
        "last_eval": dict(last_eval) if last_eval else None,
    }


@app.get("/metrics/prometheus", response_class=PlainTextResponse)
def metrics_prometheus() -> str:
    settings = get_settings()
    with get_conn() as conn:
        return prometheus_metrics(conn, settings)
