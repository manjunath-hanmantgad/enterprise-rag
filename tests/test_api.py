from pathlib import Path

from fastapi.testclient import TestClient

from enterprise_rag.api import app
from enterprise_rag.config import get_settings
from enterprise_rag.rate_limit import reset_rate_limits


def test_query_respects_document_permissions(tmp_path, monkeypatch):
    source_docs = Path(__file__).resolve().parents[1] / "demo" / "documents"
    monkeypatch.setenv("RAG_DATABASE_PATH", str(tmp_path / "rag.db"))
    monkeypatch.setenv("RAG_DOCUMENT_PATH", str(source_docs))
    monkeypatch.setenv("RAG_EVAL_SET_PATH", str(Path(__file__).resolve().parents[1] / "demo" / "evaluation_set.json"))
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    get_settings.cache_clear()

    client = TestClient(app)
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["retrieval_provider"] == "local"
    ingest = client.post("/ingest")
    assert ingest.status_code == 200
    assert ingest.json()["documents"] == 4

    employee = client.post(
        "/query",
        json={"question": "What forecast variance requires a written explanation?", "user_role": "employee"},
    )
    assert employee.status_code == 200
    employee_docs = {citation["document_id"] for citation in employee.json()["citations"]}
    assert "finance-forecast" not in employee_docs

    finance = client.post(
        "/query",
        json={"question": "What forecast variance requires a written explanation?", "user_role": "finance"},
    )
    assert finance.status_code == 200
    finance_docs = {citation["document_id"] for citation in finance.json()["citations"]}
    assert "finance-forecast" in finance_docs


def test_evaluation_endpoint_reports_no_restricted_leaks(tmp_path, monkeypatch):
    project_root = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("RAG_DATABASE_PATH", str(tmp_path / "rag.db"))
    monkeypatch.setenv("RAG_DOCUMENT_PATH", str(project_root / "demo" / "documents"))
    monkeypatch.setenv("RAG_EVAL_SET_PATH", str(project_root / "demo" / "evaluation_set.json"))
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    get_settings.cache_clear()

    client = TestClient(app)
    client.post("/ingest")
    response = client.post("/eval/run")
    assert response.status_code == 200
    body = response.json()
    assert body["total_cases"] == 4
    assert body["restricted_leak_count"] == 0


def test_api_key_role_context_controls_query_access(tmp_path, monkeypatch):
    project_root = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("RAG_DATABASE_PATH", str(tmp_path / "rag.db"))
    monkeypatch.setenv("RAG_DOCUMENT_PATH", str(project_root / "demo" / "documents"))
    monkeypatch.setenv("RAG_EVAL_SET_PATH", str(project_root / "demo" / "evaluation_set.json"))
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    get_settings.cache_clear()

    client = TestClient(app)
    client.post("/ingest")
    register = client.post(
        "/auth/register",
        json={
            "username": "finance.user",
            "full_name": "Finance User",
            "role": "finance",
            "password": "change-me-local-password",
        },
    )
    assert register.status_code == 200
    key_response = client.post("/api-keys", json={"username": "finance.user", "name": "test-key"})
    assert key_response.status_code == 200
    api_key = key_response.json()["api_key"]

    response = client.post(
        "/query",
        headers={"X-API-Key": api_key},
        json={"question": "What forecast variance requires a written explanation?", "user_role": "employee"},
    )
    assert response.status_code == 200
    docs = {citation["document_id"] for citation in response.json()["citations"]}
    assert "finance-forecast" in docs


def test_revoked_api_key_is_rejected(tmp_path, monkeypatch):
    project_root = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("RAG_DATABASE_PATH", str(tmp_path / "rag.db"))
    monkeypatch.setenv("RAG_DOCUMENT_PATH", str(project_root / "demo" / "documents"))
    monkeypatch.setenv("RAG_EVAL_SET_PATH", str(project_root / "demo" / "evaluation_set.json"))
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    get_settings.cache_clear()

    client = TestClient(app)
    client.post("/ingest")
    client.post(
        "/auth/register",
        json={
            "username": "engineer.user",
            "full_name": "Engineer User",
            "role": "engineer",
            "password": "change-me-local-password",
        },
    )
    key_response = client.post("/api-keys", json={"username": "engineer.user", "name": "test-key"})
    api_key_id = key_response.json()["id"]
    api_key = key_response.json()["api_key"]
    revoke = client.post(f"/api-keys/{api_key_id}/revoke")
    assert revoke.status_code == 200

    response = client.post(
        "/query",
        headers={"X-API-Key": api_key},
        json={"question": "What is the triage target for security incidents?", "user_role": "employee"},
    )
    assert response.status_code == 401


def test_request_id_header_is_preserved(tmp_path, monkeypatch):
    project_root = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("RAG_DATABASE_PATH", str(tmp_path / "rag.db"))
    monkeypatch.setenv("RAG_DOCUMENT_PATH", str(project_root / "demo" / "documents"))
    monkeypatch.setenv("RAG_EVAL_SET_PATH", str(project_root / "demo" / "evaluation_set.json"))
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("RAG_RETRIEVAL_PROVIDER", "local")
    get_settings.cache_clear()

    client = TestClient(app)
    response = client.get("/health", headers={"X-Request-ID": "reference-request-123"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "reference-request-123"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"


def test_ready_and_prometheus_metrics(tmp_path, monkeypatch):
    project_root = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("RAG_DATABASE_PATH", str(tmp_path / "rag.db"))
    monkeypatch.setenv("RAG_DOCUMENT_PATH", str(project_root / "demo" / "documents"))
    monkeypatch.setenv("RAG_EVAL_SET_PATH", str(project_root / "demo" / "evaluation_set.json"))
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("RAG_RETRIEVAL_PROVIDER", "local")
    get_settings.cache_clear()

    client = TestClient(app)
    client.post("/ingest")
    ready = client.get("/ready")
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"
    assert ready.json()["database"] == "ok"
    metrics = client.get("/metrics/prometheus")
    assert metrics.status_code == 200
    assert "enterprise_rag_documents_total 4" in metrics.text
    assert 'enterprise_rag_retrieval_provider_info{provider="local"} 1' in metrics.text


def test_cors_allows_configured_dashboard_origin(tmp_path, monkeypatch):
    project_root = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("RAG_DATABASE_PATH", str(tmp_path / "rag.db"))
    monkeypatch.setenv("RAG_DOCUMENT_PATH", str(project_root / "demo" / "documents"))
    monkeypatch.setenv("RAG_EVAL_SET_PATH", str(project_root / "demo" / "evaluation_set.json"))
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("RAG_RETRIEVAL_PROVIDER", "local")
    get_settings.cache_clear()

    client = TestClient(app)
    response = client.options(
        "/health",
        headers={
            "Origin": "http://127.0.0.1:8511",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:8511"


def test_config_error_returns_503_with_request_id(tmp_path, monkeypatch):
    project_root = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("RAG_DATABASE_PATH", str(tmp_path / "rag.db"))
    monkeypatch.setenv("RAG_DOCUMENT_PATH", str(project_root / "demo" / "documents"))
    monkeypatch.setenv("RAG_EVAL_SET_PATH", str(project_root / "demo" / "evaluation_set.json"))
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("RAG_RETRIEVAL_PROVIDER", "azure_ai_search")
    monkeypatch.delenv("AZURE_AI_SEARCH_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_AI_SEARCH_INDEX", raising=False)
    monkeypatch.delenv("AZURE_AI_SEARCH_KEY", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_KEY", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_EMBED_DEPLOYMENT", raising=False)
    get_settings.cache_clear()

    client = TestClient(app)
    response = client.get("/health", headers={"X-Request-ID": "config-error-1"})
    assert response.status_code == 503
    assert response.headers["X-Request-ID"] == "config-error-1"
    body = response.json()
    assert body["request_id"] == "config-error-1"
    assert "AZURE_AI_SEARCH_ENDPOINT" in body["detail"]


def test_admin_token_protects_management_endpoints_and_audit_logs(tmp_path, monkeypatch):
    project_root = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("RAG_DATABASE_PATH", str(tmp_path / "rag.db"))
    monkeypatch.setenv("RAG_DOCUMENT_PATH", str(project_root / "demo" / "documents"))
    monkeypatch.setenv("RAG_EVAL_SET_PATH", str(project_root / "demo" / "evaluation_set.json"))
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("RAG_RETRIEVAL_PROVIDER", "local")
    monkeypatch.setenv("ADMIN_TOKEN", "test-admin-token")
    get_settings.cache_clear()
    reset_rate_limits()

    client = TestClient(app)
    denied = client.post("/ingest")
    assert denied.status_code == 403

    allowed = client.post("/ingest", headers={"X-Admin-Token": "test-admin-token"})
    assert allowed.status_code == 200
    logs = client.get("/audit-logs", headers={"X-Admin-Token": "test-admin-token"})
    assert logs.status_code == 200
    assert logs.json()[0]["action"] == "documents.ingest"


def test_rate_limit_blocks_excess_requests(tmp_path, monkeypatch):
    project_root = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("RAG_DATABASE_PATH", str(tmp_path / "rag.db"))
    monkeypatch.setenv("RAG_DOCUMENT_PATH", str(project_root / "demo" / "documents"))
    monkeypatch.setenv("RAG_EVAL_SET_PATH", str(project_root / "demo" / "evaluation_set.json"))
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("RAG_RETRIEVAL_PROVIDER", "local")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "120")
    get_settings.cache_clear()
    reset_rate_limits()

    client = TestClient(app)
    client.post("/ingest")

    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "1")
    get_settings.cache_clear()
    reset_rate_limits()
    first = client.post(
        "/query",
        json={"question": "How many days per week can employees work remotely?", "user_role": "employee"},
    )
    second = client.post(
        "/query",
        json={"question": "How many days per week can employees work remotely?", "user_role": "employee"},
    )
    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["detail"] == "rate limit exceeded"


def test_query_logs_endpoint_supports_api_backed_dashboard(tmp_path, monkeypatch):
    project_root = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("RAG_DATABASE_PATH", str(tmp_path / "rag.db"))
    monkeypatch.setenv("RAG_DOCUMENT_PATH", str(project_root / "demo" / "documents"))
    monkeypatch.setenv("RAG_EVAL_SET_PATH", str(project_root / "demo" / "evaluation_set.json"))
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("RAG_RETRIEVAL_PROVIDER", "local")
    get_settings.cache_clear()
    reset_rate_limits()

    client = TestClient(app)
    client.post("/ingest")
    client.post(
        "/query",
        json={"question": "How many days per week can employees work remotely?", "user_role": "employee"},
    )
    response = client.get("/query-logs")
    assert response.status_code == 200
    body = response.json()
    assert body[0]["user_role"] == "employee"
    assert "remotely" in body[0]["question"]
