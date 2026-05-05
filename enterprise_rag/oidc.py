from __future__ import annotations

from functools import lru_cache

import httpx
import jwt
from jwt import PyJWKClient

from enterprise_rag.config import Settings


ROLE_CLAIMS = ("roles", "groups", "role")


@lru_cache(maxsize=8)
def jwks_client(jwks_url: str) -> PyJWKClient:
    return PyJWKClient(jwks_url)


def discover_jwks_uri(issuer: str) -> str:
    metadata_url = issuer.rstrip("/") + "/.well-known/openid-configuration"
    response = httpx.get(metadata_url, timeout=10)
    response.raise_for_status()
    jwks_uri = response.json().get("jwks_uri")
    if not jwks_uri:
        raise RuntimeError("OIDC metadata did not include jwks_uri.")
    return jwks_uri


def role_from_claims(claims: dict) -> str:
    for claim in ROLE_CLAIMS:
        value = claims.get(claim)
        if isinstance(value, list) and value:
            return str(value[0]).lower()
        if isinstance(value, str) and value:
            return value.lower()
    return "employee"


def validate_bearer_token(token: str, settings: Settings) -> dict:
    settings.require_auth_provider()
    jwks_url = settings.oidc_jwks_url or discover_jwks_uri(settings.oidc_issuer)
    signing_key = jwks_client(jwks_url).get_signing_key_from_jwt(token)
    claims = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=settings.oidc_audience,
        issuer=settings.oidc_issuer,
        options={"require": ["exp", "iat", "iss", "aud"]},
    )
    return {
        "subject": claims.get("sub", ""),
        "username": claims.get("preferred_username") or claims.get("upn") or claims.get("email") or claims.get("sub", ""),
        "role": role_from_claims(claims),
        "claims": claims,
    }
