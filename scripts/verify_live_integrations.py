from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from enterprise_rag.config import get_settings
from enterprise_rag.database import connect_from_settings, init_db
from enterprise_rag.key_vault import get_key_vault_secrets
from enterprise_rag.llm import AnswerGenerator
from enterprise_rag.oidc import validate_bearer_token
from enterprise_rag.retrieval import RetrievedChunk
from enterprise_rag.retrievers import AzureAISearchRetriever


@dataclass
class Check:
    name: str
    status: str
    detail: str


def chunk() -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id="live-check:0",
        document_id="live-check",
        title="Live Check",
        content="Employees may work remotely three days per week.",
        score=1.0,
        allowed_roles=["all"],
    )


def check_docker() -> Check:
    if not shutil.which("docker"):
        return Check("docker_compose", "skip", "docker command not found")
    result = subprocess.run(["docker", "compose", "config"], cwd=Path.cwd(), capture_output=True, text=True)
    if result.returncode != 0:
        return Check("docker_compose", "fail", result.stderr.strip() or result.stdout.strip())
    return Check("docker_compose", "pass", "docker compose config is valid")


def check_openai() -> Check:
    if os.getenv("LLM_PROVIDER") != "openai" or not os.getenv("OPENAI_API_KEY"):
        return Check("openai_chat", "skip", "set LLM_PROVIDER=openai and OPENAI_API_KEY")
    try:
        answer = AnswerGenerator(get_settings()).answer("How many remote days?", [chunk()])
        return Check("openai_chat", "pass", answer[:160])
    except Exception as exc:
        return Check("openai_chat", "fail", str(exc))


def check_azure_openai() -> Check:
    required = ["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_KEY", "AZURE_OPENAI_CHAT_DEPLOYMENT"]
    if not all(os.getenv(name) for name in required):
        return Check("azure_openai_chat", "skip", "set Azure OpenAI endpoint, key, and chat deployment")
    previous = os.environ.get("LLM_PROVIDER")
    os.environ["LLM_PROVIDER"] = "azure"
    get_settings.cache_clear()
    try:
        answer = AnswerGenerator(get_settings()).answer("How many remote days?", [chunk()])
        return Check("azure_openai_chat", "pass", answer[:160])
    except Exception as exc:
        return Check("azure_openai_chat", "fail", str(exc))
    finally:
        if previous is None:
            os.environ.pop("LLM_PROVIDER", None)
        else:
            os.environ["LLM_PROVIDER"] = previous
        get_settings.cache_clear()


def check_azure_ai_search() -> Check:
    required = ["AZURE_AI_SEARCH_ENDPOINT", "AZURE_AI_SEARCH_INDEX", "AZURE_AI_SEARCH_KEY"]
    if not all(os.getenv(name) for name in required):
        return Check("azure_ai_search", "skip", "set Azure AI Search endpoint, index, and key")
    previous = os.environ.get("RAG_RETRIEVAL_PROVIDER")
    os.environ["RAG_RETRIEVAL_PROVIDER"] = "azure_ai_search"
    get_settings.cache_clear()
    try:
        result = AzureAISearchRetriever(get_settings()).search(None, "remote work", "employee", 1)
        return Check("azure_ai_search", "pass", f"returned {len(result.chunks)} chunks")
    except Exception as exc:
        return Check("azure_ai_search", "fail", str(exc))
    finally:
        if previous is None:
            os.environ.pop("RAG_RETRIEVAL_PROVIDER", None)
        else:
            os.environ["RAG_RETRIEVAL_PROVIDER"] = previous
        get_settings.cache_clear()


def check_managed_storage() -> Check:
    backend = os.getenv("STORAGE_BACKEND", "sqlite")
    database_url = os.getenv("DATABASE_URL", "")
    if backend == "sqlite":
        return Check("managed_storage", "skip", "STORAGE_BACKEND=sqlite")
    if not database_url:
        return Check("managed_storage", "skip", "set DATABASE_URL")
    try:
        settings = get_settings()
        settings.require_storage_credentials()
        with connect_from_settings(settings) as conn:
            init_db(conn)
            conn.execute("SELECT 1").fetchone()
        return Check("managed_storage", "pass", f"{backend} connection and schema initialization succeeded")
    except Exception as exc:
        return Check("managed_storage", "fail", str(exc))


def check_key_vault() -> Check:
    names = [name.strip() for name in os.getenv("KEY_VAULT_SECRET_NAMES", "").split(",") if name.strip()]
    required = ["AZURE_KEY_VAULT_URL", "AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET"]
    if not names or not all(os.getenv(name) for name in required):
        return Check("key_vault", "skip", "set Key Vault URL, client credentials, and KEY_VAULT_SECRET_NAMES")
    try:
        secrets = get_key_vault_secrets(
            os.environ["AZURE_KEY_VAULT_URL"],
            os.environ["AZURE_TENANT_ID"],
            os.environ["AZURE_CLIENT_ID"],
            os.environ["AZURE_CLIENT_SECRET"],
            names,
        )
        return Check("key_vault", "pass", f"retrieved {len(secrets)} secrets")
    except Exception as exc:
        return Check("key_vault", "fail", str(exc))


def check_entra() -> Check:
    token = os.getenv("OIDC_TEST_BEARER_TOKEN")
    if not token:
        return Check("entra_oidc", "skip", "set AUTH_PROVIDER=entra and OIDC_TEST_BEARER_TOKEN")
    try:
        context = validate_bearer_token(token, get_settings())
        return Check("entra_oidc", "pass", f"user={context['username']} role={context['role']}")
    except Exception as exc:
        return Check("entra_oidc", "fail", str(exc))


def main() -> int:
    checks = [
        check_docker(),
        check_openai(),
        check_azure_openai(),
        check_azure_ai_search(),
        check_managed_storage(),
        check_key_vault(),
        check_entra(),
    ]
    print(json.dumps([check.__dict__ for check in checks], indent=2))
    return 1 if any(check.status == "fail" for check in checks) else 0


if __name__ == "__main__":
    raise SystemExit(main())
