# Roadmap

Implemented:

- local document ingestion
- SQLite metadata and chunk store
- role-aware retrieval
- citation-backed mock answers
- query metrics
- retrieval evaluation
- FastAPI endpoints
- API-backed Streamlit dashboard
- local reference users
- hashed API keys with revocation
- authenticated query role context through `X-API-Key`
- tests
- Docker files
- CI workflow
- screenshot assets
- public artifact export validation

Planned hardening:

- Add vector and hybrid retrieval modes for Azure AI Search.
- Add broader retrieval golden sets with answer-quality labels.
- Add distributed rate limiting for multi-instance deployments.
- Add managed observability integration with OpenTelemetry traces and alert rules.
