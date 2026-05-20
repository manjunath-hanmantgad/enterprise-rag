# Project 2 Issues

Track Enterprise RAG issues with symptom, root cause, fix, and verification.

## Known Environment Notes

- Docker is not available in the current shell environment, so Docker Compose verification is pending.
- Use `python3.12`; the system `python3` may be Python 3.9.6.
- Local server port binding may require elevated execution in this Codex desktop environment.

## Fixed During Initial Build

### Direct Demo Seed Import Path

- Symptom: `.venv/bin/python demo/seed_data.py` failed with `ModuleNotFoundError: No module named 'enterprise_rag'`.
- Root cause: direct script execution puts `demo/` on `sys.path`, not the project root.
- Fix: `demo/seed_data.py` now inserts the project root into `sys.path` before importing package modules.
- Verification: `.venv/bin/python demo/seed_data.py` ingested 4 documents and 4 chunks.

### Dependency Installation Requires Network Approval

- Symptom: `.venv/bin/pip install -r requirements.txt` failed inside the sandbox with DNS resolution errors for `pypi.org`.
- Root cause: network access is restricted in the default sandbox.
- Fix: reran the same install command with approved elevated network access.
- Verification: dependencies installed and `.venv/bin/pytest` passed.

### Settings Read Environment Too Early

- Symptom: tests that patched `RAG_DATABASE_PATH` still reused the default local database and hit duplicate demo users.
- Root cause: `Settings` field defaults called `os.getenv()` at import time instead of when `get_settings()` was called.
- Fix: `get_settings()` now reads environment variables at runtime and remains cache-clearable for tests.
- Verification: `.venv/bin/pytest` passes with isolated temporary databases.

### Streamlit Dashboard Import Path

- Symptom: `.venv/bin/streamlit run dashboard/app.py` started but the app raised `ModuleNotFoundError: No module named 'enterprise_rag'`.
- Root cause: Streamlit executes the dashboard file with `dashboard/` as the script context, so the project root was not on `sys.path`.
- Fix: `dashboard/app.py` now inserts the project root into `sys.path` before importing project modules.
- Verification: dashboard returns HTTP 200 on `http://127.0.0.1:8511`.

### Browser Screenshot Viewport

- Symptom: the in-app browser captured valid screenshots at a narrow viewport and did not expose `setViewportSize`.
- Root cause: the browser-use runtime in this environment returns screenshot objects but does not support viewport resizing through the available API.
- Fix: saved screenshots through the screenshot object's base64 output and documented the current assets.
- Verification: `file demo/enterprise-rag-*.png` reports valid PNG files.

### Query Metrics Schema Too Narrow

- Symptom: adding `retrieval_provider: "local"` to query metrics caused `QueryResponse` validation errors.
- Root cause: `QueryResponse.metrics` allowed only `float | int`, but retrieval provider is a string label.
- Fix: expanded the metrics schema to `float | int | str`.
- Verification: `.venv/bin/pytest` passes and `/query` returns `metrics.retrieval_provider`.

### Operational Middleware Added

- Symptom: the API had request IDs but did not yet expose readiness checks, security headers, CORS settings, structured request logs, or Prometheus-style metrics.
- Root cause: first implementation focused on demo behavior before deployment operations.
- Fix: added `/ready`, configurable CORS, default security headers, JSON request logging, and `/metrics/prometheus`.
- Verification: `.venv/bin/pytest` passes; live `/ready`, CORS preflight, and `/metrics/prometheus` smoke checks pass.

### Management Security Controls Added

- Symptom: ingestion, local user creation, API key management, and evaluation runs were open in local mode with no optional production guard.
- Root cause: the first local-first implementation optimized for immediate demo usability.
- Fix: added optional `ADMIN_TOKEN`, `X-Admin-Token` enforcement for management endpoints, admin audit logs, and in-memory rate limiting.
- Verification: `.venv/bin/pytest` passes; live `/audit-logs` and `/metrics/prometheus` smoke checks pass.

### Cloud Provider Adapters Added

- Symptom: OpenAI, Azure OpenAI, and Azure AI Search were represented mostly as placeholders.
- Root cause: local-first implementation came before cloud adapter implementation.
- Fix: added OpenAI and Azure OpenAI chat completion REST paths plus Azure AI Search REST retrieval.
- Verification: mocked provider tests pass; live credential verification is pending until provider credentials and Azure resources are available.

### OIDC / Entra Validation Added

- Symptom: production identity was represented only as a placeholder.
- Root cause: local demo auth came before cloud identity integration.
- Fix: added OIDC/Entra bearer token validation against issuer, audience, expiry, and JWKS signing keys.
- Verification: generated RSA/JWKS tests pass; live Entra tenant verification is pending until tenant/app registration details are available.
