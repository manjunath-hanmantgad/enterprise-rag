# Runbook — Enterprise RAG

## Service overview
Enterprise RAG provides role-aware document retrieval and citation-backed answers through a FastAPI API. If this service is unavailable, document Q&A, access-control enforcement, and evaluation reporting are interrupted.

## Health checks
| Endpoint | Expected | What it means |
|---|---|---|
| `GET /health` | `200` with provider/retrieval/auth/storage fields | Core config and provider validation passed |
| `GET /ready` | `200` with `{"status":"ready",...}` | DB reachable and document count query works |
| `GET /metrics/prometheus` | `200` text payload | Metrics scraping path is healthy |
| `GET /metrics` | `200` metrics JSON | Operational counters and last eval are readable |

## Common failure scenarios

### Provider config failures (`/health` returns 503)
**Symptom:** `GET /health` or `GET /ready` returns `503` with missing config detail.
**Action:**
1. Confirm `.env` values for `LLM_PROVIDER`, `RAG_RETRIEVAL_PROVIDER`, and `STORAGE_BACKEND`.
2. For local demo, set `LLM_PROVIDER=mock` and `RAG_RETRIEVAL_PROVIDER=local`.
3. Retry `curl http://localhost:8002/health`.

### Document retrieval returns weak/no citations
**Symptom:** `/query` answers fallback with insufficient source message.
**Action:**
1. Re-ingest docs: `python demo/seed_data.py`.
2. Check `/documents` count.
3. Re-run evaluation endpoint: `POST /eval/run`.

### Access-control leakage concerns
**Symptom:** unauthorized roles appear to receive restricted citations.
**Action:**
1. Reproduce with and without `X-API-Key`.
2. Validate role on key owner via `/api-keys`.
3. Run evaluation set and confirm `restricted_leak_count` remains `0`.

### Rate limit errors
**Symptom:** frequent `429 rate limit exceeded`.
**Action:**
1. Inspect `RATE_LIMIT_PER_MINUTE` in environment.
2. Increase for demo/staging if needed.
3. Retry from a clean client session.

## Rollback procedure
```bash
az containerapp revision list \
  --name <ENTERPRISE_RAG_CONTAINER_APP> \
  --resource-group <RESOURCE_GROUP>

az containerapp revision activate \
  --name <ENTERPRISE_RAG_CONTAINER_APP> \
  --resource-group <RESOURCE_GROUP> \
  --revision <PREVIOUS_REVISION_NAME>
```

## Log access
```bash
# Local logs
docker compose logs -f api

# Azure logs
az containerapp logs show \
  --name <ENTERPRISE_RAG_CONTAINER_APP> \
  --resource-group <RESOURCE_GROUP> \
  --follow
```

## Contacts / escalation
- Primary owner: [fill in]
- Secondary owner: [fill in]
- Escalation SLA: [fill in]
