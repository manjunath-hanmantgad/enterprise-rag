# Deployment

## Local

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
.venv/bin/python demo/seed_data.py
.venv/bin/uvicorn enterprise_rag.api:app --host 127.0.0.1 --port 8002
```

## Docker

Docker files are included for containerized runtime validation.

```bash
docker compose up --build
```

Run this command in an environment where Docker is installed and running.

## Azure Path

Recommended target architecture:

- Azure Container Apps for API and dashboard.
- Azure Blob Storage for source documents.
- Azure AI Search for hybrid retrieval.
- Azure OpenAI for embeddings and answer generation.
- Azure PostgreSQL or Cosmos DB for metadata and audit logs.
- Azure Key Vault for secrets.
- Application Insights for logs and metrics.
- Entra ID for authentication and role claims.

Azure mode fails fast when required `AZURE_*` settings are missing.

Operational environment variables:

```env
CORS_ORIGINS=https://your-dashboard.example.com
SECURITY_HEADERS_ENABLED=true
JSON_LOGS=true
ADMIN_TOKEN=replace_with_strong_management_token
RATE_LIMIT_PER_MINUTE=120
DASHBOARD_API_URL=https://your-api.example.com
DASHBOARD_ADMIN_TOKEN=replace_with_strong_management_token
```

Recommended platform probes:

- Liveness: `GET /health`
- Readiness: `GET /ready`
- Metrics scraping: `GET /metrics/prometheus`

For Azure retrieval mode:

```env
RAG_RETRIEVAL_PROVIDER=azure_ai_search
AZURE_AI_SEARCH_ENDPOINT=
AZURE_AI_SEARCH_INDEX=
AZURE_AI_SEARCH_KEY=
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_KEY=
AZURE_OPENAI_EMBED_DEPLOYMENT=
```

The Azure AI Search REST adapter is implemented for keyword search over `chunk_id`, `document_id`, `title`, `content`, and `allowed_roles`. Live verification requires an Azure AI Search service and compatible index.

OpenAI and Azure OpenAI chat generation are implemented through chat completions REST endpoints. Live verification requires provider credentials.

Managed storage:

```env
STORAGE_BACKEND=azure_postgres
DATABASE_URL=postgresql://user:password@host:5432/enterprise_rag?sslmode=require
```

The app includes a PostgreSQL-compatible storage adapter for this mode. When credentials are available, run `scripts/verify_live_integrations.py` to open the database, initialize tables, and verify a query succeeds.

OIDC configuration:

```env
AUTH_PROVIDER=entra
OIDC_ISSUER=
OIDC_AUDIENCE=
OIDC_JWKS_URL=
```

The app validates bearer JWTs against issuer, audience, expiration, and JWKS signing keys. Entra validation requires tenant details and an app registration with matching audience and role or group claims.

## Live Integration Verification

After Docker or cloud credentials are configured, run:

```bash
.venv/bin/python scripts/verify_live_integrations.py
```

The script reports `pass`, `skip`, or `fail` for:

- Docker Compose configuration
- OpenAI chat generation
- Azure OpenAI chat generation
- Azure AI Search retrieval
- managed storage configuration
- Azure Key Vault secret retrieval
- Entra/OIDC bearer token validation

Unconfigured integrations are reported as `skip`, not failure, so each integration can be verified independently.

## Azure Key Vault

Key Vault verification uses Entra client credentials and the Key Vault secrets REST API.

```env
AZURE_KEY_VAULT_URL=https://your-vault.vault.azure.net
AZURE_TENANT_ID=
AZURE_CLIENT_ID=
AZURE_CLIENT_SECRET=
KEY_VAULT_SECRET_NAMES=OPENAI-API-KEY,ADMIN-TOKEN
KEY_VAULT_SECRET_MAPPINGS=OPENAI-API-KEY=OPENAI_API_KEY,ADMIN-TOKEN=ADMIN_TOKEN
KEY_VAULT_OVERRIDE_EXISTING=false
```

When `KEY_VAULT_SECRET_NAMES` is set, the API loads those secrets during configuration. By default, a secret named `OPENAI-API-KEY` maps to `OPENAI_API_KEY`; explicit mappings should be used for names that do not map cleanly to environment variable names, such as `DATABASE-URL=DATABASE_URL`.
