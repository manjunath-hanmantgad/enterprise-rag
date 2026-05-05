from enterprise_rag.config import Settings
from enterprise_rag.database import _translate_placeholders, init_db, connect


def test_sqlite_storage_initializes_schema(tmp_path):
    conn = connect(tmp_path / "rag.db")
    init_db(conn)
    conn.execute("INSERT INTO documents (id, title, department, allowed_roles, source_path, checksum) VALUES (?, ?, ?, ?, ?, ?)", (
        "doc-1",
        "Document",
        "Operations",
        "all",
        "demo/documents/doc-1.md",
        "checksum",
    ))
    conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    assert count == 1


def test_postgres_storage_configuration_is_allowed_when_database_url_exists(tmp_path):
    settings = Settings(
        app_env="test",
        database_path=tmp_path / "rag.db",
        document_path=tmp_path,
        eval_set_path=tmp_path / "eval.json",
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
        storage_backend="azure_postgres",
        database_url="postgresql://user:pass@localhost:5432/enterprise_rag",
        auth_provider="local",
        oidc_issuer="",
        oidc_audience="",
        oidc_jwks_url="",
        azure_key_vault_url="",
        azure_tenant_id="",
        azure_client_id="",
        azure_client_secret="",
        key_vault_secret_names=[],
        key_vault_secret_mappings={},
    )
    settings.require_storage_credentials()


def test_postgres_placeholder_translation():
    sql = "SELECT * FROM documents WHERE id = ? LIMIT ?"
    assert _translate_placeholders(sql) == "SELECT * FROM documents WHERE id = %s LIMIT %s"
