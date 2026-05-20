# Three Design Decisions That Shaped the Enterprise RAG Retrieval Pipeline

*Enterprise RAG — A practitioner's build log | Post 3 of 6*

---

A retrieval pipeline has more design surface than it appears. The technology choices — vector search, LLM provider, storage engine — get most of the attention. The structural choices — where filtering happens, how evaluation is wired, what the dashboard connects to — determine whether the system actually works correctly in a production environment.

This post documents three structural decisions I made in Enterprise RAG, the constraint that drove each one, and the cost I accepted.

---

## Decision 1: Lexical retrieval before semantic — sequencing, not a permanent choice

The default retrieval implementation uses token cosine similarity against a local SQLite chunk store (`RAG_RETRIEVAL_PROVIDER=local`). Not vector embeddings. Not a managed search index. Lexical scoring.

This was a sequencing decision, not a technology preference.

**The constraint:** Access control validation requires a deterministic retrieval baseline. If retrieval results vary across runs — because embedding models update, because vector indices are rebuilt, because approximate nearest neighbor algorithms introduce non-determinism — the evaluation set becomes unreliable. A `restricted_leak_count` of zero means nothing if retrieval is non-deterministic and the same query might return different chunks tomorrow.

Lexical retrieval is fully deterministic. Given the same document corpus and the same query, it returns the same ranked chunk list every time. That makes the evaluation set a reliable regression test rather than a probabilistic snapshot.

**The accepted cost:** Lexical scoring does not capture semantic similarity. A question about "headcount reduction" will not retrieve a chunk that uses the phrase "workforce restructuring" unless there is token overlap. Semantic retrieval closes that gap — at the cost of determinism in the local validation environment.

The Azure AI Search adapter (`RAG_RETRIEVAL_PROVIDER=azure_ai_search`) is implemented for production use, where semantic and hybrid query modes are available. The retrieval provider is a configuration switch, not a code change. Switching from local to Azure AI Search does not alter the access control layer, the evaluation runner, or the API surface.

---

## Decision 2: API-backed dashboard — not direct database access

The Streamlit dashboard (`dashboard/app.py`) connects to the FastAPI API layer, not the database directly. Every dashboard operation — querying documents, fetching metrics, running evaluations, reviewing the citation log — goes through an authenticated API call.

This was not a minor implementation choice. It was a deliberate architectural boundary.

**The constraint:** A dashboard that reads the database directly cannot be deployed in a containerized or cloud environment without granting the dashboard container database credentials. That creates a credential distribution problem: every new environment where the dashboard runs needs database access, which widens the credential surface.

An API-backed dashboard has a single credential requirement: the `DASHBOARD_API_URL` and optionally `DASHBOARD_ADMIN_TOKEN`. The dashboard container never holds database credentials. It holds only the API location and the management token. The API enforces authorization. The database credentials stay with the API container.

**The accepted cost:** Every dashboard operation adds one network hop compared to direct database access. For a local development setup this is negligible. For a cloud-deployed dashboard querying an API on the same virtual network, it is also negligible. The cost is only relevant if the dashboard is running in a significantly different network zone from the API — which would itself be an unusual deployment topology.

The secondary benefit: the API-backed dashboard tests the public API surface on every dashboard interaction. If the dashboard shows correct data, the API is returning correct data. That is a form of continuous integration that direct database access cannot provide.

---

## Decision 3: Evaluation runner as a live API endpoint — not an offline script

The evaluation runner is exposed as `POST /eval/run` — a standard API endpoint that runs the evaluation set against the live query pipeline and returns metrics directly.

Most RAG evaluation setups I have seen are offline scripts: pull a golden set, run retrieval, compare results, write a report. The script does not call the production API. It calls the retrieval components directly, often with mocked or simplified versions of the access control layer.

**The constraint:** If the evaluation script bypasses the access control layer, it cannot detect access control failures. A `restricted_leak_count` computed by calling the retriever directly — without going through the role filter — will always be zero, regardless of whether the filter is actually working in production.

By routing evaluation through `POST /eval/run`, which calls `POST /query` internally, the evaluation runner tests the entire pipeline: authentication handling, role filter, retrieval, generation, and citation assembly. Every evaluation case exercises the same code path that a real user request exercises.

**The accepted cost:** Live evaluation runs against the production database. In a high-traffic environment, running a large evaluation set could add query load. The mitigation is to run evaluations at low-traffic windows or against a staging environment — not to move evaluation back to a disconnected script.

The current evaluation set is small and optimized for repeatable access-control checks. Extending it with larger golden sets, human relevance labels, and answer correctness checks is a documented roadmap item.

---

## One decision I made explicitly not to make yet

Role metadata is currently embedded in document front matter — each markdown document has a `allowed_roles` field that specifies which roles can retrieve it. This is correct for a local deterministic environment where document metadata is under engineering control.

In production, role context should come from the identity provider — Entra ID claims or OIDC bearer token attributes — not from request body parameters or document-embedded metadata alone. I did not implement full Entra ID role claim integration because it requires a live Azure tenant to validate. The configuration path is documented and the `AUTH_PROVIDER=entra` setting is implemented. The end-to-end test of role-from-identity-claim requires a real identity provider.

That is a known gap. It is in the production considerations section of `docs/security.md`, not hidden in implementation comments.

---

## Current limits

- Lexical retrieval does not capture semantic similarity. Queries with no token overlap with document chunks will not retrieve relevant results even when the content is semantically related.
- Evaluation set size is calibrated for local access-control validation. Answer quality evaluation — correctness labels, human relevance ratings — is a planned extension.
- Entra ID role claim integration requires a live Azure tenant for end-to-end validation. The local implementation uses request-body role parameters, which must not be trusted in production without API key authentication.
- The `POST /eval/run` endpoint requires the `ADMIN_TOKEN` when management protection is enabled. Evaluation runs in protected environments require the admin credential.

---

## Next engineering step

Add one document to the corpus with `allowed_roles: ["finance"]`, run `POST /eval/run`, and verify that the new document appears in the blocked count for non-finance evaluation cases. That single test confirms the role filter is reading document metadata correctly and applying it before scoring.

---

## One question for you

Does your internal RAG evaluation pipeline call the same API endpoints that production queries use, or does it call retrieval components directly? If it bypasses the access control layer, does your `restricted_leak_count` metric actually measure anything?

---

*Next post: The evaluation metrics that matter for enterprise RAG — and why pass rate alone is not enough to validate a system that handles restricted documents.*
