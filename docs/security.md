# Security

## Implemented

- No secrets are committed.
- `.env.example` contains non-secret configuration templates only.
- Mock mode requires no provider key.
- Role-based filtering runs before retrieval scoring.
- Local users can be created for role-based access validation.
- API keys are generated with random tokens and stored as SHA-256 hashes.
- API keys can be revoked, and revoked keys are rejected by `/query`.
- `X-API-Key` role context overrides request-body role input.
- Management endpoints can be protected with `ADMIN_TOKEN`.
- In-memory rate limiting can be configured with `RATE_LIMIT_PER_MINUTE`.
- Administrative actions are written to `audit_logs`.
- CORS origins are configurable with `CORS_ORIGINS`.
- Security headers are emitted by default.
- Restricted documents are included in evaluation checks.
- Query logs store citations and metrics for auditability.
- Azure Key Vault secrets can be loaded at startup with explicit secret-to-environment mappings.

## Production Considerations

- Use authenticated identity claims for employee access in managed environments.
- Use Microsoft Entra ID or another OIDC provider.
- `AUTH_PROVIDER=entra` and `AUTH_PROVIDER=oidc` validate bearer JWTs against issuer, audience, expiration, and JWKS signing keys.
- Use managed API gateway or OAuth client credentials for service-to-service access.
- Store provider keys, admin tokens, and `DATABASE_URL` in Azure Key Vault or the hosting platform secret store.
- Encrypt databases and object storage at rest.
- Define retention controls for prompts, answers, and citations.
- Add CORS restrictions for browser clients.
- Replace local in-memory rate limiting with gateway or Redis-backed rate limiting for multi-instance production.
- Add tenant isolation before multi-tenant deployment.

## Management Endpoints

When `ADMIN_TOKEN` is set, these endpoints require `X-Admin-Token`:

- `POST /ingest`
- `POST /auth/register`
- `POST /api-keys`
- `GET /api-keys`
- `POST /api-keys/{api_key_id}/revoke`
- `GET /audit-logs`
- `POST /eval/run`

Set `ADMIN_TOKEN` for any shared, hosted, or externally accessible environment.

## Entra ID / OIDC

Set:

```env
AUTH_PROVIDER=entra
OIDC_ISSUER=https://login.microsoftonline.com/<tenant-id>/v2.0
OIDC_AUDIENCE=api://enterprise-rag
OIDC_JWKS_URL=https://login.microsoftonline.com/<tenant-id>/discovery/v2.0/keys
```

When enabled, `/query` can derive retrieval role context from bearer token claims. Role mapping checks `roles`, then `groups`, then `role`, and defaults to `employee` when no role claim is present.

## Managed Secrets

Set:

```env
AZURE_KEY_VAULT_URL=https://your-vault.vault.azure.net
AZURE_TENANT_ID=<tenant-id>
AZURE_CLIENT_ID=<app-client-id>
AZURE_CLIENT_SECRET=<app-client-secret>
KEY_VAULT_SECRET_NAMES=OPENAI-API-KEY,DATABASE-URL,ADMIN-TOKEN
KEY_VAULT_SECRET_MAPPINGS=OPENAI-API-KEY=OPENAI_API_KEY,DATABASE-URL=DATABASE_URL,ADMIN-TOKEN=ADMIN_TOKEN
```

The application fetches listed secrets during configuration. Existing environment variables are preserved unless `KEY_VAULT_OVERRIDE_EXISTING=true` is set.

## Data Handling

The included reference documents are synthetic. Production ingestion should include PII classification, sensitive document labeling, and explicit retention policies before storing prompts or generated answers.
