# Enterprise RAG Walkthrough

This walkthrough proves that the same document question can produce different accessible citations depending on the user's role.

## Scenario

Acme Operations has four internal documents:

- Hybrid Work Policy: accessible to all employees.
- Customer Support SLA: accessible to all employees.
- Incident Response Runbook: restricted to engineers and admins.
- Finance Forecast Controls: restricted to finance and admins.

## Run

```bash
cd enterprise-rag
.venv/bin/python demo/seed_data.py
.venv/bin/uvicorn enterprise_rag.api:app --host 127.0.0.1 --port 8002
```

Ask as an engineer:

```bash
curl -X POST http://127.0.0.1:8002/query \
  -H "Content-Type: application/json" \
  -d '{"question":"What is the triage target for security incidents?","user_role":"engineer"}'
```

Ask as an employee:

```bash
curl -X POST http://127.0.0.1:8002/query \
  -H "Content-Type: application/json" \
  -d '{"question":"What forecast variance requires a written explanation?","user_role":"employee"}'
```

Create or use the seeded finance user:

```bash
curl -X POST http://127.0.0.1:8002/api-keys \
  -H "Content-Type: application/json" \
  -d '{"username":"fatima.finance","name":"finance-access-key"}'
```

Ask as finance using the returned key:

```bash
curl -X POST http://127.0.0.1:8002/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: rag_returned_key_here" \
  -d '{"question":"What forecast variance requires a written explanation?","user_role":"employee"}'
```

Run evaluation:

```bash
curl -X POST http://127.0.0.1:8002/eval/run
```

Expected outcome:

- Employee questions cite only documents with `allowed_roles: all`.
- Engineer questions can cite the incident runbook.
- Finance API-key questions can cite finance forecast controls even if the request body says `employee`, because the server uses the key owner role.
- Revoked API keys are rejected.
- Evaluation reports `restricted_leak_count: 0`.

## Screenshot Assets

Current screenshots are captured at desktop width:

- `demo/enterprise-rag-dashboard.png`
- `demo/enterprise-rag-citations.png`
- `demo/enterprise-rag-permission-test.png`
- `demo/enterprise-rag-evaluation.png`

Refresh them after meaningful UI changes.
