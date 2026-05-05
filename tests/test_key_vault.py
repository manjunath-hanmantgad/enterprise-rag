import httpx

from enterprise_rag.config import get_settings
from enterprise_rag.key_vault import get_client_credentials_token, get_key_vault_secret


def test_client_credentials_token_request(monkeypatch):
    captured = {}

    def fake_post(url, data, timeout):
        captured.update({"url": url, "data": data, "timeout": timeout})
        return httpx.Response(200, request=httpx.Request("POST", url), json={"access_token": "token"})

    monkeypatch.setattr("enterprise_rag.key_vault.httpx.post", fake_post)
    token = get_client_credentials_token("tenant", "client", "secret", "https://vault.azure.net/.default")
    assert token == "token"
    assert "tenant/oauth2/v2.0/token" in captured["url"]
    assert captured["data"]["grant_type"] == "client_credentials"


def test_get_key_vault_secret(monkeypatch):
    captured = {}

    def fake_get(url, headers, timeout):
        captured.update({"url": url, "headers": headers, "timeout": timeout})
        return httpx.Response(200, request=httpx.Request("GET", url), json={"value": "secret-value"})

    monkeypatch.setattr("enterprise_rag.key_vault.httpx.get", fake_get)
    value = get_key_vault_secret("https://vault.vault.azure.net", "OPENAI-API-KEY", "token")
    assert value == "secret-value"
    assert "/secrets/OPENAI-API-KEY" in captured["url"]
    assert "api-version=2025-07-01" in captured["url"]
    assert captured["headers"]["Authorization"] == "Bearer token"


def test_key_vault_secrets_can_populate_runtime_env(monkeypatch):
    monkeypatch.setenv("KEY_VAULT_SECRET_NAMES", "OPENAI-API-KEY,DATABASE-URL")
    monkeypatch.setenv("KEY_VAULT_SECRET_MAPPINGS", "OPENAI-API-KEY=OPENAI_API_KEY,DATABASE-URL=DATABASE_URL")
    monkeypatch.setenv("AZURE_KEY_VAULT_URL", "https://vault.vault.azure.net")
    monkeypatch.setenv("AZURE_TENANT_ID", "tenant")
    monkeypatch.setenv("AZURE_CLIENT_ID", "client")
    monkeypatch.setenv("AZURE_CLIENT_SECRET", "secret")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    def fake_get_key_vault_secrets(vault_url, tenant_id, client_id, client_secret, secret_names):
        assert vault_url == "https://vault.vault.azure.net"
        assert tenant_id == "tenant"
        assert client_id == "client"
        assert client_secret == "secret"
        assert secret_names == ["OPENAI-API-KEY", "DATABASE-URL"]
        return {"OPENAI-API-KEY": "openai-secret", "DATABASE-URL": "postgresql://example"}

    monkeypatch.setattr("enterprise_rag.config.get_key_vault_secrets", fake_get_key_vault_secrets)
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.openai_api_key == "openai-secret"
    assert settings.database_url == "postgresql://example"
