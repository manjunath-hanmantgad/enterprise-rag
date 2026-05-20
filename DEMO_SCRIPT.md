# Demo Script — Enterprise RAG

**Duration:** 15–20 minutes  
**Audience:** Security, platform, and data leadership  
**What you need open:** `http://localhost:8002/docs`, dashboard, terminal

## Pre-demo setup (do this 10 minutes before)
- [ ] Run: `make up`
- [ ] Seed baseline data: `make seed`
- [ ] Verify API: `curl http://localhost:8002/health`
- [ ] Open API docs: `http://localhost:8002/docs`

## The problem you're solving (2 minutes)
> Say: "Most internal RAG demos ignore access control and citation quality. Enterprise RAG enforces role-based retrieval and shows exactly which source documents were used for each answer."

## The solution overview (3 minutes)
> Show `docs/architecture.md` and summarize: ingestion, chunk retrieval, role filtering, and answer generation with citations.

## Live demo walkthrough (10 minutes)

### Step 1 — Ingest documents
Run `POST /ingest` (with `X-Admin-Token` if configured).

Expected output: document and chunk counts.

### Step 2 — Create a finance identity and API key
Call `POST /auth/register` then `POST /api-keys`.

Expected output: API key prefix and role metadata.

### Step 3 — Access control contrast
1. Call `/query` as plain `employee` for a finance policy question.
2. Call the same `/query` with finance API key.

Expected output: finance citation appears only with finance role.

### Step 4 — Key revocation control
Call `POST /api-keys/{id}/revoke`, then retry `/query` with that key.

Expected output: revoked key is rejected.

### Step 5 — Evaluation summary
Call `POST /eval/run` and show result fields including `restricted_leak_count`.

Expected output: pass summary and no restricted leakage.

## Business value close (2 minutes)
> Say: "The system proves retrieval quality and authorization boundaries with repeatable evaluation metrics, not just anecdotal responses."

## Fallback plan
If API is down:
- Show screenshots in `demo/`.
- Walk through `demo/evaluation_set.json` and `docs/evaluation.md`.
- Replay curl commands from terminal history with expected outputs.

## Common demo gotchas
- Running Docker map `8002:8000`; calling `localhost:8000` from host will fail.
- Forgetting `X-Admin-Token` when `ADMIN_TOKEN` is set.
- Missing seed data leads to low/no retrieval confidence.
