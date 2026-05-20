from __future__ import annotations

import httpx
from azure.identity import DefaultAzureCredential


def get_client_credentials_token(tenant_id: str, client_id: str, client_secret: str, scope: str) -> str:
    response = httpx.post(
        f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials",
            "scope": scope,
        },
        timeout=20,
    )
    response.raise_for_status()
    token = response.json().get("access_token")
    if not token:
        raise RuntimeError("Entra token response did not include access_token.")
    return token


def get_key_vault_secret(vault_url: str, secret_name: str, access_token: str) -> str:
    url = f"{vault_url.rstrip('/')}/secrets/{secret_name}?api-version=2025-07-01"
    response = httpx.get(url, headers={"Authorization": f"Bearer {access_token}"}, timeout=20)
    response.raise_for_status()
    value = response.json().get("value")
    if value is None:
        raise RuntimeError(f"Key Vault secret {secret_name} response did not include value.")
    return value


def get_key_vault_secrets(
    vault_url: str,
    tenant_id: str = "",
    client_id: str = "",
    client_secret: str = "",
    secret_names: list[str] | None = None,
) -> dict[str, str]:
    if not secret_names:
        return {}

    # Primary: DefaultAzureCredential — works automatically in Azure Container Apps with Managed Identity.
    try:
        token = DefaultAzureCredential().get_token("https://vault.azure.net/.default").token
        return {name: get_key_vault_secret(vault_url, name, token) for name in secret_names}
    except Exception:
        pass

    # Fallback: client credentials for local dev when client_secret is configured.
    if tenant_id and client_id and client_secret:
        token = get_client_credentials_token(tenant_id, client_id, client_secret, "https://vault.azure.net/.default")
        return {name: get_key_vault_secret(vault_url, name, token) for name in secret_names}

    raise RuntimeError(
        "Key Vault authentication failed: DefaultAzureCredential did not succeed "
        "and AZURE_CLIENT_SECRET is not configured for local dev fallback."
    )
