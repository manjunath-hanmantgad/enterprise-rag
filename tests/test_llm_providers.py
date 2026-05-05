import httpx

from enterprise_rag.config import Settings
from enterprise_rag.llm import AnswerGenerator
from enterprise_rag.retrieval import RetrievedChunk


def _settings(provider: str) -> Settings:
    return Settings(
        app_env="test",
        database_path=":memory:",
        document_path="demo/documents",
        eval_set_path="demo/evaluation_set.json",
        llm_provider=provider,
        openai_model="gpt-4o-mini",
        retrieval_provider="local",
        openai_api_key="test-key",
        azure_openai_endpoint="https://example.openai.azure.com",
        azure_openai_key="azure-key",
        azure_openai_chat_deployment="chat",
        azure_openai_embed_deployment="embed",
        azure_openai_api_version="2024-10-21",
        azure_ai_search_endpoint="",
        azure_ai_search_index="",
        azure_ai_search_key="",
        cors_origins=[],
        security_headers_enabled=True,
        json_logs=True,
        admin_token="",
        rate_limit_per_minute=120,
        storage_backend="sqlite",
        database_url="",
        auth_provider="local",
        oidc_issuer="",
        oidc_audience="",
        oidc_jwks_url="",
    )


def _chunk() -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id="doc:0",
        document_id="doc",
        title="Policy",
        content="Employees may work remotely three days per week.",
        score=1.0,
        allowed_roles=["all"],
    )


def test_openai_answer_uses_chat_completions(monkeypatch):
    captured = {}

    def fake_post(url, headers, json, timeout):
        captured.update({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={"choices": [{"message": {"content": "Employees may work remotely three days per week [1]."}}]},
        )

    monkeypatch.setattr("enterprise_rag.llm.httpx.post", fake_post)
    answer = AnswerGenerator(_settings("openai")).answer("How many remote days?", [_chunk()])
    assert "three days" in answer
    assert captured["url"] == "https://api.openai.com/v1/chat/completions"
    assert captured["json"]["model"] == "gpt-4o-mini"
    assert captured["headers"]["Authorization"] == "Bearer test-key"


def test_azure_openai_answer_uses_deployment_endpoint(monkeypatch):
    captured = {}

    def fake_post(url, headers, json, timeout):
        captured.update({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={"choices": [{"message": {"content": "Azure answer [1]."}}]},
        )

    monkeypatch.setattr("enterprise_rag.llm.httpx.post", fake_post)
    answer = AnswerGenerator(_settings("azure")).answer("Question?", [_chunk()])
    assert answer == "Azure answer [1]."
    assert "/openai/deployments/chat/chat/completions" in captured["url"]
    assert "api-version=2024-10-21" in captured["url"]
    assert captured["headers"]["api-key"] == "azure-key"
