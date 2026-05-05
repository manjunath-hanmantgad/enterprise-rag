# Release Readiness

Project status: **public repository ready**.

The project provides a complete local-first RAG implementation with production-oriented interfaces for managed storage, identity, model providers, retrieval providers, secrets, metrics, and deployment validation. Cloud integrations are enabled by environment configuration and can be verified independently when target credentials are available.

## Implemented

- Credential-free local runtime.
- FastAPI query and management API.
- API-backed Streamlit dashboard.
- Local markdown ingestion.
- SQLite metadata, chunk, query, evaluation, API key, and audit storage for local mode.
- PostgreSQL/Azure PostgreSQL storage adapter and schema initialization for managed production storage.
- Role-aware retrieval before scoring.
- Citation-backed answers.
- Real OpenAI and Azure OpenAI chat generation paths.
- Azure AI Search REST retrieval adapter.
- Local users, hashed API keys, revocation, admin-token management protection, and OIDC/Entra JWT validation.
- Request IDs, security headers, CORS, readiness checks, structured logs, and Prometheus-style metrics.
- Retrieval evaluation with restricted leakage checks.
- Reference data, screenshots, README, full docs, tests, CI workflow, Docker files, and public artifact validation.
- Azure Key Vault startup secret loading with explicit secret-to-environment mappings.
- Live integration verification harness for Docker, OpenAI, Azure OpenAI, Azure AI Search, managed storage, Key Vault, and Entra/OIDC.

## Public Repository Validation

Before publishing, run:

```bash
.venv/bin/pytest
.venv/bin/python scripts/prepare_public_release.py --destination ../enterprise-rag-public
```

The generated public artifact excludes local databases, internal issue history, private planning docs, virtual environments, and the release script.

## External Environment Validation

These checks depend on resources outside the repository and are intentionally verified with user-provided infrastructure:

- Docker Compose runtime validation in a Docker-enabled environment.
- OpenAI and Azure OpenAI live calls with provider credentials.
- Azure AI Search query validation against the target index.
- Azure PostgreSQL connectivity with the target `DATABASE_URL`.
- Azure Key Vault secret retrieval with vault and app credentials.
- Entra/OIDC bearer-token validation with the target tenant and app registration.

The verification harness reports unconfigured external checks as `skip`, allowing each integration to be validated independently without blocking local operation.

## Deployment Notes

- Use `ADMIN_TOKEN` for any shared or externally accessible environment.
- Use `AUTH_PROVIDER=entra` or `AUTH_PROVIDER=oidc` for employee-facing access.
- Use `STORAGE_BACKEND=azure_postgres` with TLS-enabled `DATABASE_URL` for managed cloud storage.
- Store model keys, management tokens, and database credentials in Azure Key Vault or the hosting platform secret store.
- Move rate limiting to an API gateway or shared limiter for multi-instance deployments.
