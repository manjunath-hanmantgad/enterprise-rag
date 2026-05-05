import pytest
import httpx

from enterprise_rag.config import get_settings
from enterprise_rag.retrieval import cosine_score, role_allowed
from enterprise_rag.retrievers import AzureAISearchRetriever, get_retriever


def test_role_allowed_supports_all_and_specific_roles():
    assert role_allowed("employee", ["all"])
    assert role_allowed("engineer", ["engineer", "admin"])
    assert not role_allowed("employee", ["finance", "admin"])


def test_cosine_score_prefers_matching_content():
    question = "security incident triage target"
    matching = "security incidents require triage within fifteen minutes"
    unrelated = "employees may request ergonomic reimbursement"
    assert cosine_score(question, matching) > cosine_score(question, unrelated)


def test_default_retriever_is_local(monkeypatch):
    monkeypatch.delenv("RAG_RETRIEVAL_PROVIDER", raising=False)
    get_settings.cache_clear()
    assert get_retriever(get_settings()).provider_name == "local"


def test_azure_retriever_requires_clear_credentials(monkeypatch):
    monkeypatch.setenv("RAG_RETRIEVAL_PROVIDER", "azure_ai_search")
    monkeypatch.delenv("AZURE_AI_SEARCH_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_AI_SEARCH_INDEX", raising=False)
    monkeypatch.delenv("AZURE_AI_SEARCH_KEY", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_KEY", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_EMBED_DEPLOYMENT", raising=False)
    get_settings.cache_clear()
    with pytest.raises(RuntimeError, match="AZURE_AI_SEARCH_ENDPOINT"):
        get_retriever(get_settings())


def test_azure_ai_search_retriever_maps_results(monkeypatch):
    monkeypatch.setenv("RAG_RETRIEVAL_PROVIDER", "azure_ai_search")
    monkeypatch.setenv("AZURE_AI_SEARCH_ENDPOINT", "https://search.example.com")
    monkeypatch.setenv("AZURE_AI_SEARCH_INDEX", "docs")
    monkeypatch.setenv("AZURE_AI_SEARCH_KEY", "search-key")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://openai.example.com")
    monkeypatch.setenv("AZURE_OPENAI_KEY", "openai-key")
    monkeypatch.setenv("AZURE_OPENAI_EMBED_DEPLOYMENT", "embed")
    get_settings.cache_clear()
    captured = {}

    def fake_post(url, headers, json, timeout):
        captured.update({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={
                "value": [
                    {
                        "@search.score": 2.5,
                        "chunk_id": "finance:0",
                        "document_id": "finance",
                        "title": "Finance",
                        "content": "Forecast variance greater than five percent requires explanation.",
                        "allowed_roles": ["finance"],
                    }
                ]
            },
        )

    monkeypatch.setattr("enterprise_rag.retrievers.httpx.post", fake_post)
    result = AzureAISearchRetriever(get_settings()).search(None, "forecast variance", "finance", 3)
    assert result.provider == "azure_ai_search"
    assert result.chunks[0].document_id == "finance"
    assert "allowed_roles/any" in captured["json"]["filter"]
    assert captured["headers"]["api-key"] == "search-key"
