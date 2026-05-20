# Four Metrics That Actually Tell You Whether Your Enterprise RAG Is Working

*Enterprise RAG — A practitioner's build log | Post 4 of 6*

---

RAG evaluation in most implementations stops at one question: did the system retrieve the document that was supposed to be retrieved?

That is the right question for a consumer search product. It is an incomplete question for an enterprise knowledge system where some documents are accessible to all employees and others are restricted by role. In that environment, retrieval correctness is necessary but not sufficient. You also need to know whether restricted documents leaked into answers they should not have influenced.

Enterprise RAG implements four metrics. Each measures a different failure mode. Together they constitute a validation standard that is appropriate for internal knowledge systems handling mixed-sensitivity documents.

---

## The four metrics and what each catches

**Pass rate** — the percentage of evaluation cases where expected documents were retrieved and forbidden documents were not.

This is the composite metric. A case passes only when both conditions hold simultaneously: the expected documents appear in the citation set and no forbidden documents appear. A system that retrieves all expected documents but also leaks one forbidden document does not pass that case. Pass rate does not reward partial correctness.

**Restricted leakage count** — the number of evaluation cases that returned at least one forbidden document in the citation set.

This is the most operationally critical metric for an enterprise deployment. A restricted leakage count of zero means the role filter is working correctly across every test case in the evaluation set. Any non-zero value indicates a specific failure to investigate — which case, which document, which role, which query.

**Citation coverage** — the average number of citations returned per evaluation case.

Low citation coverage indicates that the retrieval system is returning answers without grounding them in source documents. In an enterprise context, an answer without citations cannot be verified, audited, or traced back to a source document. Citation coverage is a proxy for answer auditability.

**Average latency (ms)** — the mean query execution time across all evaluation cases.

Latency is not a quality metric. It is an operational baseline. If latency increases after a retrieval configuration change — switching from local lexical to Azure AI Search, adding a reranking step, increasing chunk count — the evaluation run captures it. Latency regression during evaluation is a signal worth investigating before deploying the change.

---

## What the evaluation output looks like

Running `POST /eval/run` returns all four metrics in a single response alongside the per-case results:

```json
{
  "pass_rate": 1.0,
  "restricted_leak_count": 0,
  "citation_coverage": 2.4,
  "average_latency_ms": 38.2,
  "cases": [...]
}
```

Each case in the result array includes the question, the role used, the retrieved document IDs, and a pass/fail indicator. A failed case shows exactly which expected document was missing or which forbidden document leaked.

![Enterprise RAG evaluation summary — pass rate, leakage count, citation coverage, and latency](enterprise-rag-evaluation.png)

The evaluation runner calls `POST /query` internally for each case, which means it exercises the entire pipeline: authentication, role filter, retrieval, generation, and citation assembly. The metrics reflect actual system behavior, not a mocked retrieval path.

---

## Why the evaluation set structure matters as much as the metrics

The evaluation set (`demo/evaluation_set.json`) defines each case with three fields alongside the question and role:

- **Expected document IDs** — documents that must appear in the citation set for the case to pass
- **Forbidden document IDs** — documents that must not appear in the citation set

Both lists are required for every case. An evaluation case without forbidden document IDs cannot measure restricted leakage. An evaluation set without any cases involving restricted documents cannot validate access control at all.

Most RAG golden sets I have reviewed define expected documents only. They measure retrieval recall but provide no signal on access control correctness. Adding forbidden document IDs to every test case involving a restricted document is the minimum viable evaluation standard for an enterprise knowledge system.

![Enterprise RAG citation-backed answer — cited sources visible and traceable](enterprise-rag-citations.png)

---

## What the evaluation set does not yet cover

The current evaluation set is optimized for access-control validation and citation tracing. It does not yet cover:

- **Answer correctness** — whether the generated answer is factually accurate relative to the cited documents. This requires human relevance labels or LLM-as-judge evaluation templates.
- **Semantic retrieval quality** — the lexical retriever handles the current evaluation set well. A semantic retrieval configuration may return different ranked results that pass the access-control checks but rank differently by relevance.
- **Regression thresholds in CI** — the evaluation runner is callable from CI. The current setup does not fail a CI run if pass rate drops below a threshold. Adding a threshold check (`if restricted_leak_count > 0: fail`) to the CI workflow is the practical next hardening step.

These are documented roadmap items, not silent gaps.

---

## Current limits

- Evaluation set size is small — calibrated for repeatable local validation, not production-scale coverage.
- Answer correctness evaluation requires human labels or an LLM judge. Neither is implemented in the current evaluation runner.
- Latency benchmarks reflect the local SQLite retrieval path. Azure AI Search latency profiles will differ.
- The evaluation runner requires the `ADMIN_TOKEN` when management protection is enabled, which prevents accidental evaluation runs in shared environments.

---

## Next engineering step

Review the evaluation cases in `demo/evaluation_set.json` and count how many include at least one forbidden document ID. If any cases have only expected documents, add a forbidden document ID for a restricted document that should not be retrievable by that role. Then re-run `POST /eval/run` and verify the leakage count remains zero.

---

## One question for you

Does your current RAG evaluation set include forbidden document IDs alongside expected document IDs? If not, how do you validate that restricted documents are not influencing answers for unauthorized roles?

---

*Next post: Security decisions in Enterprise RAG — how API keys, audit logs, and the order of role enforcement work together to make the system defensible.*
