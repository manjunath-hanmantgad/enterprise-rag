from datetime import datetime, timedelta, timezone
import base64

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from enterprise_rag.config import Settings
from enterprise_rag.oidc import role_from_claims, validate_bearer_token


def _b64_uint(value: int) -> str:
    raw = value.to_bytes((value.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _settings() -> Settings:
    return Settings(
        app_env="test",
        database_path=":memory:",
        document_path="demo/documents",
        eval_set_path="demo/evaluation_set.json",
        llm_provider="mock",
        openai_model="gpt-4o-mini",
        retrieval_provider="local",
        openai_api_key="",
        azure_openai_endpoint="",
        azure_openai_key="",
        azure_openai_chat_deployment="",
        azure_openai_embed_deployment="",
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
        auth_provider="entra",
        oidc_issuer="https://login.microsoftonline.com/test-tenant/v2.0",
        oidc_audience="api://enterprise-rag",
        oidc_jwks_url="https://login.microsoftonline.com/test-tenant/discovery/v2.0/keys",
    )


def test_role_from_claims_prefers_roles():
    assert role_from_claims({"roles": ["Finance"]}) == "finance"
    assert role_from_claims({"groups": ["Engineer"]}) == "engineer"
    assert role_from_claims({}) == "employee"


def test_validate_bearer_token_with_jwks(monkeypatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_numbers = private_key.public_key().public_numbers()
    jwk = {
        "kty": "RSA",
        "kid": "test-key",
        "use": "sig",
        "alg": "RS256",
        "n": _b64_uint(public_numbers.n),
        "e": _b64_uint(public_numbers.e),
    }
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "iss": "https://login.microsoftonline.com/test-tenant/v2.0",
            "aud": "api://enterprise-rag",
            "sub": "user-1",
            "preferred_username": "finance@example.com",
            "roles": ["finance"],
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=10)).timestamp()),
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )

    class FakeJwksClient:
        def get_signing_key_from_jwt(self, jwt_token):
            del jwt_token

            class Key:
                key = private_key.public_key()

            return Key()

    monkeypatch.setattr("enterprise_rag.oidc.jwks_client", lambda url: FakeJwksClient())
    context = validate_bearer_token(token, _settings())
    assert context["username"] == "finance@example.com"
    assert context["role"] == "finance"
