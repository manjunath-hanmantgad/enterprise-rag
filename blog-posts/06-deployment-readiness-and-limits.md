# What Enterprise RAG Is Ready For Today and What Production Deployment Actually Requires

*Enterprise RAG — A practitioner's build log | Post 6 of 6*

---

This series has documented a system built to a specific standard: one where access control is enforced before retrieval scoring, where every answer includes traceable citations, and where the evaluation set measures restricted document leakage rather than retrieval relevance alone.

This final post answers the question that matters most for teams considering this as a foundation: what works today, what needs to be in place before this handles real internal documents in a production environment, and what the gap between those two states actually looks like.

---

## What is fully operational today

Every item below runs locally without external dependencies or provider credentials.

**Document pipeline:**
- Markdown document ingestion with front-matter role metadata (`POST /ingest`)
- SQLite metadata and chunk store with document and chunk count metrics
- Lexical retrieval with token cosine similarity scoring

**Query and access control:**
- Role-based candidate filter applied before retrieval scoring
- Citation-backed answer generation in deterministic mock mode
- `RBAC_blocked_count` logged per query — tracks how many chunks were filtered
- Role derivation from `X-API-Key` header, preventing request-body role elevation

**API and authentication:**
- FastAPI query API (`POST /query`) with health probes at `GET /health`
- Local user registration with role assignment (`POST /auth/register`)
- API key creation, listing, and revocation (`POST /api-keys`, `POST /api-keys/{id}/revoke`)
- SHA-256 key hash storage — raw key never persisted after creation
- Management endpoint protection via `ADMIN_TOKEN`

**Evaluation:**
- Evaluation runner via `POST /eval/run` — calls live query pipeline, not a mocked path
- Four metrics per run: pass rate, restricted leakage count, citation coverage, average latency
- Per-case results with expected vs. retrieved document IDs and pass/fail indicators

**Operational controls:**
- Audit log for all administrative actions (`GET /audit-logs`)
- Query log with citations, role, latency, and RBAC metrics
- Prometheus-style operational metrics endpoint
- Security headers enabled by default, CORS explicitly configured
- Structured JSON request logging (`JSON_LOGS=true`)
- In-memory rate limiting per client (`RATE_LIMIT_PER_MINUTE`)

**Infrastructure:**
- API-backed Streamlit dashboard — no direct database access from the UI
- Docker files for containerized runtime validation
- GitHub Actions CI workflow
- Azure AI Search retrieval adapter implemented and configuration-selectable
- OpenAI and Azure OpenAI generation adapters configuration-selectable

---

## The Azure deployment path

The local runtime maps directly to an Azure deployment topology:

```
Employee → Microsoft Entra ID
               ↓
       Azure Container Apps: API + Dashboard
               ↓
       Azure AI Search (retrieval)
       Azure OpenAI (answer generation)
       Azure PostgreSQL or Cosmos DB (metadata + audit logs)
       Azure Blob Storage (source documents)
               ↓
       Azure Key Vault (secrets)
       Application Insights (logs + metrics)
```

Switching from local to Azure requires environment variable changes only. No code changes. No schema migrations between SQLite and PostgreSQL — the SQLAlchemy layer handles both. Azure mode fails fast when required `AZURE_*` settings are missing rather than silently degrading to a local fallback.

---

## What production deployment requires beyond the current implementation

**Entra ID or OIDC role derivation from identity claims.** The local implementation derives role from API key registration. Production deployment should derive role from authenticated identity token claims — not from request parameters or static key registration. The `AUTH_PROVIDER=entra` configuration path is implemented. End-to-end validation requires a live Azure tenant.

**Semantic or hybrid retrieval.** The local lexical retriever is deterministic and validates access control correctly. It does not match the retrieval quality of embedding-based semantic search for queries without token overlap with document chunks. Azure AI Search vector and hybrid query modes are the planned production retrieval path.

**Distributed rate limiting.** The in-memory rate limiter does not share state across multiple API instances. Horizontal scaling requires Redis-backed or API gateway rate limiting.

**PII classification and retention policies.** The reference document corpus is synthetic. Before ingesting real internal documents — HR records, finance reports, incident logs — the ingestion pipeline should classify content for PII, apply sensitivity labels, and enforce explicit data retention policies for stored queries and generated answers.

**Tenant isolation.** The current implementation is single-organization. A deployment serving multiple business units with strict data isolation between them requires a tenant isolation layer at the data model and query pipeline level.

**Broader evaluation set.** The current evaluation set is calibrated for access-control validation across a small synthetic corpus. A production evaluation set requires human relevance labels, answer correctness checks, and a regression threshold integrated into the CI workflow.

---

## An honest assessment

Enterprise RAG demonstrates the architecture that matters for internal knowledge systems: pre-retrieval access control, citation-backed answers, and an evaluation standard that measures restricted document leakage. The local implementation is complete, testable, and fully reproducible without provider credentials.

The gap to production is real and specific. Entra ID integration, semantic retrieval, distributed rate limiting, PII handling, and tenant isolation are well-understood engineering problems with clear solutions. None of them require rethinking the core pipeline — the access control order, the citation model, and the evaluation structure remain intact.

For a team building an internal document Q&A system: the architecture here is worth adopting. The hardening list above is the production backlog, not a reason to start from scratch.

---

## What I would implement next

The highest-impact single item is Entra ID role derivation in production. The entire value of pre-retrieval access control depends on the role being trustworthy. In a local environment with API key role binding, that trust is reasonable. In a production environment with hundreds of employees, role must come from an authenticated identity provider — not from a manually registered key that may become stale when someone changes teams or leaves the organization.

The concrete step: configure `AUTH_PROVIDER=entra`, map Entra group claims to retrieval roles, and validate that the role filter receives the correct role from the token rather than from the request body. That single change makes the access control guarantee durable against organizational changes.

---

## One question for you

When an employee changes roles or leaves your organization, how quickly does your internal knowledge system stop serving them documents from their previous role? Is that enforced at the identity provider level or at the document system level?

---

*This concludes the Enterprise RAG build log series.*

---

## Full series index

1. The Access Control Gap That Makes Most Enterprise RAG Systems Dangerous
2. How Enterprise RAG Is Structured: Why Access Control Comes Before Retrieval Scoring
3. Three Design Decisions That Shaped the Enterprise RAG Retrieval Pipeline
4. Four Metrics That Actually Tell You Whether Your Enterprise RAG Is Working
5. Security Controls in Enterprise RAG: Keys, Audit Logs, and the Hierarchy That Prevents Role Elevation
6. What Enterprise RAG Is Ready For Today and What Production Deployment Actually Requires *(this post)*

*Add Medium post URLs to each title above after publishing.*
