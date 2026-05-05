# API

Base URL in local mode: `http://127.0.0.1:8002`

Responses include `X-Request-ID` for correlation. Clients can provide the header on requests; otherwise the API generates one.

When `ADMIN_TOKEN` is configured, management endpoints require `X-Admin-Token`.

## `GET /health`

Returns service status, active LLM provider, and active retrieval provider.

Provider configuration errors return `503` with:

```json
{
  "detail": "configuration error message",
  "request_id": "correlation-id"
}
```

## `GET /ready`

Checks provider configuration, database connectivity, and current document count.

## `POST /ingest`

Loads markdown files from `RAG_DOCUMENT_PATH`, parses metadata, chunks document bodies, and stores them in the configured metadata store.

Response:

```json
{"documents":4,"chunks":4}
```

## `GET /documents`

Returns ingested document metadata including allowed roles.

## `POST /auth/register`

Creates a local user for API-key based access control.

```json
{
  "username": "fatima.finance",
  "full_name": "Fatima Finance",
  "role": "finance",
  "password": "change-me-local-password"
}
```

## `POST /api-keys`

Creates an API key for an existing local user. The raw key is returned once and only the hash is stored.

```json
{
  "username": "fatima.finance",
  "name": "finance-access-key"
}
```

## `GET /api-keys`

Lists key metadata, prefix, owner, role, created timestamp, and revocation status. Raw key values are not returned.

## `POST /api-keys/{api_key_id}/revoke`

Revokes an active API key. Subsequent requests with that key return `401`.

## `GET /audit-logs`

Lists recent administrative actions. Requires `X-Admin-Token` when `ADMIN_TOKEN` is configured.

## `POST /query`

Request:

```json
{
  "question": "What is the triage target for security incidents?",
  "user_role": "engineer",
  "top_k": 4
}
```

When `X-API-Key` is provided, the API derives `user_role` from the key owner and ignores the request body role. This makes access control server-authoritative instead of trusting caller-supplied role values.

When `AUTH_PROVIDER=oidc` or `AUTH_PROVIDER=entra`, `/query` can also derive role context from `Authorization: Bearer <token>`.

```bash
curl -X POST http://127.0.0.1:8002/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: rag_example_key" \
  -d '{"question":"What forecast variance requires a written explanation?","user_role":"employee"}'
```

Response includes:

- `answer`
- `citations`
- `latency_ms`
- `metrics.retrieved_count`
- `metrics.blocked_count`
- `metrics.top_score`

## `GET /query-logs`

Returns recent query log rows for the API-backed dashboard activity view.

## `POST /eval/run`

Runs the retrieval evaluation set configured by `RAG_EVAL_SET_PATH`.

## `GET /metrics`

Returns document, chunk, query, latency, and latest evaluation summary.

The response also includes the active `retrieval_provider`.

## `GET /metrics/prometheus`

Returns Prometheus-style text metrics for service scraping.
