# How Enterprise RAG Is Structured: Why Access Control Comes Before Retrieval Scoring

*Enterprise RAG — A practitioner's build log | Post 2 of 6*

---

The architecture of a RAG system is determined by one decision above all others: where in the pipeline does access control happen?

Get that order wrong and the entire system is structurally insecure regardless of how well the retrieval scores or how accurate the generated answers are. Get it right and the security guarantee holds even as the document corpus grows, roles change, and retrieval algorithms are swapped.

In Enterprise RAG, the order is fixed: role filtering runs before retrieval scoring. That single constraint drives every component boundary in the system.

---

## Request flow: the order that matters

```
User → POST /query (question + user_role)
           ↓
       Load all candidate document chunks
           ↓
       Apply role filter — unauthorized chunks removed here
           ↓
       Score accessible chunks (token cosine similarity)
           ↓
       Select top citations
           ↓
       Generate answer from cited context only
           ↓
       Persist query metrics and citation log
           ↓
       Return: answer + citations + latency + retrieval metrics
```

The role filter sits between loading candidates and scoring them. The generator never receives an unauthorized chunk. The citation list cannot include what the generator never saw. The audit log records exactly which chunks were retrieved, which were filtered, and how many were blocked by role.

---

## Component breakdown

**FastAPI query API (`enterprise_rag/api.py`).** Receives authenticated requests on `POST /query`. Derives the retrieval role from the `X-API-Key` header when present — key-holder role overrides any role supplied in the request body, preventing role elevation by callers. Falls back to request body role for unauthenticated queries.

**Role-based candidate filter.** Loads document chunks from SQLite, then filters by the `allowed_roles` metadata field on each chunk. Accepted values include `all`, `engineer`, `finance`, and `admin`. A chunk with `allowed_roles: ["finance", "admin"]` is excluded from engineer and employee queries before a single relevance score is computed.

**Lexical retriever.** Scores the filtered candidate set using token cosine similarity. Because filtering happened upstream, the scorer operates only on chunks the requesting role is authorized to see. Retrieval quality metrics — retrieved chunk count, top retrieval score, RBAC-blocked chunk count — are captured per query.

**Mock answer generator.** Builds a deterministic answer from the top cited chunks. In `LLM_PROVIDER=mock` mode this runs without any provider key, making local validation fully reproducible. OpenAI and Azure OpenAI adapters are configuration-selectable for production use.

**Query log and metrics store (SQLite).** Every query persists: question, role, citations, latency, retrieved chunk count, and RBAC-blocked chunk count. This log is the audit record. It answers not just "what did the system return?" but "what was blocked and why?"

**Evaluation runner (`POST /eval/run`).** Runs the evaluation set against the live query pipeline. Reports pass rate, restricted leakage count, citation coverage, and average latency. Because the evaluation runner calls the same `/query` endpoint as a real user, it tests the entire pipeline end-to-end — not a mocked retrieval path.

**API-backed Streamlit dashboard.** The dashboard calls the FastAPI layer rather than reading the database directly. This is a deliberate design choice: the same API boundary used for the UI can be retained for containerized or Azure deployment without changes.

![Enterprise RAG dashboard — query metrics, citation log, and evaluation summary](enterprise-rag-dashboard.png)

---

## How Azure AI Search fits the same pipeline

The local retrieval implementation uses lexical scoring against SQLite chunks. The Azure AI Search adapter replaces the retriever component while keeping the same access control boundary:

```
Azure AI Search filter (before results are returned):
allowed_roles/any(role: role eq 'all' or role eq '<user_role>')
```

The filter is applied server-side at the search index before results are returned to the application. The application layer role filter provides defense in depth, but the primary enforcement happens at the index level when Azure AI Search is the retrieval provider.

This is the correct architecture for a production deployment: access control enforced at two layers — index filter and application filter — so a misconfiguration at one layer does not compromise the other.

---

## The local-to-Azure configuration switch

Every component in the local architecture has a direct Azure counterpart:

| Local | Azure |
|---|---|
| SQLite metadata and chunks | Azure PostgreSQL or Cosmos DB |
| Local markdown files | Azure Blob Storage |
| Lexical retriever | Azure AI Search |
| Mock answer generator | Azure OpenAI |
| Local API and dashboard | Azure Container Apps |
| Environment variables | Azure Key Vault |
| `print` / file logs | Application Insights |
| Local users and hashed keys | Microsoft Entra ID |

Switching between local and Azure requires only environment variable changes. No code path changes, no schema migrations between local and PostgreSQL — SQLAlchemy handles both.

---

## Current limits

- The local retriever uses lexical scoring. Semantic similarity and hybrid retrieval are planned Azure AI Search extensions. Lexical scoring is sufficient for deterministic local validation but will not match embedding-based relevance in production.
- The dashboard is single-instance. Distributed session state and multi-instance deployments require additional coordination.
- Rate limiting is in-memory per instance. Multi-instance production deployments require Redis-backed or API gateway rate limiting.
- Tenant isolation for multi-organization deployments is a documented production consideration, not yet implemented.

---

## Next engineering step

Query the system as `employee` role for a question that has a known restricted finance document in scope. Inspect the `rbac_blocked_count` field in the query log. Confirm that the blocked count is non-zero — meaning the filter ran and excluded chunks — before the answer was generated.

---

## One question for you

In your current RAG architecture, at what stage does access control run — before chunk scoring, after chunk scoring, or only at the citation display layer? Do you have a metric that tracks how many chunks were filtered per query?

---

*Next post: Three design decisions that shaped the retrieval pipeline — why lexical retrieval before semantic, why API-backed dashboard over direct database access, and why evaluation is built into the API rather than run as a separate offline script.*
