# Operations

## Health

`GET /health` validates the active provider configuration and returns service status.

`GET /ready` validates provider configuration, confirms the database can be queried, and returns the current document count. Use `/health` for lightweight liveness and `/ready` for startup/deployment readiness checks.

## Request Correlation

Every API response includes `X-Request-ID`. Clients may send their own `X-Request-ID` header; otherwise the API creates one. Configuration and provider errors include the same request id in the JSON response body.

## Request Logging

The API emits structured JSON logs by default. Each request log includes:

- request id
- method
- path
- status code
- latency in milliseconds

Set `JSON_LOGS=false` for plain text logs in local debugging.

## Security Headers And CORS

Security headers are enabled by default:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: no-referrer`
- `Permissions-Policy: camera=(), microphone=(), geolocation=()`

Configure browser origins with `CORS_ORIGINS`. Local defaults allow the Streamlit dashboard on `127.0.0.1:8511` and `localhost:8511`.

## Management Protection

Set `ADMIN_TOKEN` to require `X-Admin-Token` on management endpoints such as ingestion, user creation, API key management, audit logs, and evaluation runs. Keep it configured for shared, hosted, or externally accessible environments.

For the Streamlit dashboard, set:

```env
DASHBOARD_API_URL=http://127.0.0.1:8002
DASHBOARD_ADMIN_TOKEN=your_admin_token_when_enabled
```

The dashboard calls the FastAPI service and does not access SQLite directly.

## Rate Limiting

`RATE_LIMIT_PER_MINUTE` controls an in-memory request limiter for local and single-instance deployments. For multi-instance production, move rate limiting to an API gateway, ingress controller, or shared Redis-backed limiter.

## Audit Logs

Administrative actions are recorded in `audit_logs` and can be read with:

```bash
curl http://127.0.0.1:8002/audit-logs -H "X-Admin-Token: your_admin_token"
```

## Live Integration Checks

Run the external verification harness after configuring Docker or cloud credentials:

```bash
.venv/bin/python scripts/verify_live_integrations.py
```

The command is safe to run incrementally. Integrations without configured credentials are marked `skip`.

## Metrics

`GET /metrics` exposes:

- document count
- chunk count
- query count
- average latency
- latest evaluation result

`GET /metrics/prometheus` exposes Prometheus-style text metrics:

- `enterprise_rag_documents_total`
- `enterprise_rag_chunks_total`
- `enterprise_rag_queries_total`
- `enterprise_rag_query_latency_average_ms`
- `enterprise_rag_restricted_leaks_total`
- `enterprise_rag_retrieval_provider_info`

## Reference Data Reset

Run:

```bash
.venv/bin/python demo/seed_data.py
```

This reloads documents and chunks from `demo/documents`. Query logs and evaluation runs are retained so the dashboard can show activity over time.

The seed script also creates local reference users:

- `emma.employee`
- `eric.engineer`
- `fatima.finance`
- `ava.admin`

All seeded users use `change-me-local-password`.

## Monitoring Roadmap

Production operations should add OpenTelemetry traces, alert rules for leakage regressions, and scheduled retrieval evaluations.
