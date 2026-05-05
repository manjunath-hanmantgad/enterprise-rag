from functools import lru_cache
import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from enterprise_rag.key_vault import get_key_vault_secrets


load_dotenv()


class Settings(BaseModel):
    app_env: str
    database_path: Path
    document_path: Path
    eval_set_path: Path
    llm_provider: str
    openai_model: str
    retrieval_provider: str
    openai_api_key: str
    azure_openai_endpoint: str
    azure_openai_key: str
    azure_openai_chat_deployment: str
    azure_openai_embed_deployment: str
    azure_openai_api_version: str
    azure_ai_search_endpoint: str
    azure_ai_search_index: str
    azure_ai_search_key: str
    cors_origins: list[str]
    security_headers_enabled: bool
    json_logs: bool
    admin_token: str
    rate_limit_per_minute: int
    storage_backend: str
    database_url: str
    auth_provider: str
    oidc_issuer: str
    oidc_audience: str
    oidc_jwks_url: str
    azure_key_vault_url: str = ""
    azure_tenant_id: str = ""
    azure_client_id: str = ""
    azure_client_secret: str = ""
    key_vault_secret_names: list[str] = Field(default_factory=list)
    key_vault_secret_mappings: dict[str, str] = Field(default_factory=dict)

    def require_provider_credentials(self) -> None:
        provider = self.llm_provider.lower()
        if provider == "mock":
            return
        if provider == "openai" and not self.openai_api_key:
            raise RuntimeError("LLM_PROVIDER=openai requires OPENAI_API_KEY.")
        if provider == "azure":
            missing = [
                name
                for name, value in {
                    "AZURE_OPENAI_ENDPOINT": self.azure_openai_endpoint,
                    "AZURE_OPENAI_KEY": self.azure_openai_key,
                    "AZURE_OPENAI_CHAT_DEPLOYMENT": self.azure_openai_chat_deployment,
                    "AZURE_OPENAI_EMBED_DEPLOYMENT": self.azure_openai_embed_deployment,
                }.items()
                if not value
            ]
            if missing:
                raise RuntimeError(f"LLM_PROVIDER=azure is missing: {', '.join(missing)}.")
        if provider not in {"mock", "openai", "azure"}:
            raise RuntimeError("LLM_PROVIDER must be one of: mock, openai, azure.")

    def require_retrieval_credentials(self) -> None:
        provider = self.retrieval_provider.lower()
        if provider == "local":
            return
        if provider == "openai":
            if not self.openai_api_key:
                raise RuntimeError("RAG_RETRIEVAL_PROVIDER=openai requires OPENAI_API_KEY.")
            raise RuntimeError("RAG_RETRIEVAL_PROVIDER=openai is reserved for a future vector index implementation.")
        if provider == "azure_ai_search":
            missing = [
                name
                for name, value in {
                    "AZURE_AI_SEARCH_ENDPOINT": self.azure_ai_search_endpoint,
                    "AZURE_AI_SEARCH_INDEX": self.azure_ai_search_index,
                    "AZURE_AI_SEARCH_KEY": self.azure_ai_search_key,
                    "AZURE_OPENAI_ENDPOINT": self.azure_openai_endpoint,
                    "AZURE_OPENAI_KEY": self.azure_openai_key,
                    "AZURE_OPENAI_EMBED_DEPLOYMENT": self.azure_openai_embed_deployment,
                }.items()
                if not value
            ]
            if missing:
                raise RuntimeError(f"RAG_RETRIEVAL_PROVIDER=azure_ai_search is missing: {', '.join(missing)}.")
            return
        raise RuntimeError("RAG_RETRIEVAL_PROVIDER must be one of: local, openai, azure_ai_search.")

    def require_storage_credentials(self) -> None:
        if self.storage_backend == "sqlite":
            return
        if self.storage_backend in {"postgres", "azure_postgres"}:
            if not self.database_url:
                raise RuntimeError(f"STORAGE_BACKEND={self.storage_backend} requires DATABASE_URL.")
            return
        raise RuntimeError("STORAGE_BACKEND must be one of: sqlite, postgres, azure_postgres.")

    def require_auth_provider(self) -> None:
        if self.auth_provider == "local":
            return
        if self.auth_provider in {"oidc", "entra"}:
            missing = [
                name
                for name, value in {
                    "OIDC_ISSUER": self.oidc_issuer,
                    "OIDC_AUDIENCE": self.oidc_audience,
                    "OIDC_JWKS_URL": self.oidc_jwks_url,
                }.items()
                if not value
            ]
            if missing:
                raise RuntimeError(f"AUTH_PROVIDER={self.auth_provider} is missing: {', '.join(missing)}.")
            return
        raise RuntimeError("AUTH_PROVIDER must be one of: local, oidc, entra.")


def _parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _parse_secret_mappings(value: str) -> dict[str, str]:
    mappings: dict[str, str] = {}
    for item in _parse_csv(value):
        if "=" not in item:
            continue
        secret_name, env_name = item.split("=", 1)
        mappings[secret_name.strip()] = env_name.strip()
    return mappings


def _secret_name_to_env(secret_name: str) -> str:
    return secret_name.replace("-", "_").upper()


def _load_key_vault_env() -> None:
    secret_names = _parse_csv(os.getenv("KEY_VAULT_SECRET_NAMES", ""))
    if not secret_names:
        return
    required = {
        "AZURE_KEY_VAULT_URL": os.getenv("AZURE_KEY_VAULT_URL", ""),
        "AZURE_TENANT_ID": os.getenv("AZURE_TENANT_ID", ""),
        "AZURE_CLIENT_ID": os.getenv("AZURE_CLIENT_ID", ""),
        "AZURE_CLIENT_SECRET": os.getenv("AZURE_CLIENT_SECRET", ""),
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise RuntimeError(f"KEY_VAULT_SECRET_NAMES is set but Key Vault configuration is missing: {', '.join(missing)}.")
    mappings = _parse_secret_mappings(os.getenv("KEY_VAULT_SECRET_MAPPINGS", ""))
    override_existing = os.getenv("KEY_VAULT_OVERRIDE_EXISTING", "false").lower() == "true"
    secrets = get_key_vault_secrets(
        required["AZURE_KEY_VAULT_URL"],
        required["AZURE_TENANT_ID"],
        required["AZURE_CLIENT_ID"],
        required["AZURE_CLIENT_SECRET"],
        secret_names,
    )
    for secret_name, secret_value in secrets.items():
        env_name = mappings.get(secret_name, _secret_name_to_env(secret_name))
        if override_existing or not os.getenv(env_name):
            os.environ[env_name] = secret_value


@lru_cache
def get_settings() -> Settings:
    _load_key_vault_env()
    settings = Settings(
        app_env=os.getenv("APP_ENV", "local"),
        database_path=Path(os.getenv("RAG_DATABASE_PATH", "storage/enterprise_rag.db")),
        document_path=Path(os.getenv("RAG_DOCUMENT_PATH", "demo/documents")),
        eval_set_path=Path(os.getenv("RAG_EVAL_SET_PATH", "demo/evaluation_set.json")),
        llm_provider=os.getenv("LLM_PROVIDER", "mock"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        retrieval_provider=os.getenv("RAG_RETRIEVAL_PROVIDER", "local"),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
        azure_openai_key=os.getenv("AZURE_OPENAI_KEY", ""),
        azure_openai_chat_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", ""),
        azure_openai_embed_deployment=os.getenv("AZURE_OPENAI_EMBED_DEPLOYMENT", ""),
        azure_openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
        azure_ai_search_endpoint=os.getenv("AZURE_AI_SEARCH_ENDPOINT", ""),
        azure_ai_search_index=os.getenv("AZURE_AI_SEARCH_INDEX", ""),
        azure_ai_search_key=os.getenv("AZURE_AI_SEARCH_KEY", ""),
        cors_origins=[
            origin.strip()
            for origin in os.getenv("CORS_ORIGINS", "http://127.0.0.1:8511,http://localhost:8511").split(",")
            if origin.strip()
        ],
        security_headers_enabled=os.getenv("SECURITY_HEADERS_ENABLED", "true").lower() == "true",
        json_logs=os.getenv("JSON_LOGS", "true").lower() == "true",
        admin_token=os.getenv("ADMIN_TOKEN", ""),
        rate_limit_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "120")),
        storage_backend=os.getenv("STORAGE_BACKEND", "sqlite"),
        database_url=os.getenv("DATABASE_URL", ""),
        auth_provider=os.getenv("AUTH_PROVIDER", "local"),
        oidc_issuer=os.getenv("OIDC_ISSUER", ""),
        oidc_audience=os.getenv("OIDC_AUDIENCE", ""),
        oidc_jwks_url=os.getenv("OIDC_JWKS_URL", ""),
        azure_key_vault_url=os.getenv("AZURE_KEY_VAULT_URL", ""),
        azure_tenant_id=os.getenv("AZURE_TENANT_ID", ""),
        azure_client_id=os.getenv("AZURE_CLIENT_ID", ""),
        azure_client_secret=os.getenv("AZURE_CLIENT_SECRET", ""),
        key_vault_secret_names=_parse_csv(os.getenv("KEY_VAULT_SECRET_NAMES", "")),
        key_vault_secret_mappings=_parse_secret_mappings(os.getenv("KEY_VAULT_SECRET_MAPPINGS", "")),
    )
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    return settings
