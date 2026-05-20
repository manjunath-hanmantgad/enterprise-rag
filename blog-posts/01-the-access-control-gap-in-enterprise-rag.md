# The Access Control Gap That Makes Most Enterprise RAG Systems Dangerous

*Enterprise RAG — A practitioner's build log | Post 1 of 6*

---

There is a retrieval failure mode that does not show up in accuracy benchmarks: a system that finds the right document but returns it to the wrong person.

Most RAG evaluation frameworks measure whether the retrieved chunks are relevant to the question. Few measure whether those chunks should have been retrievable at all given who asked. In an enterprise context — where the same knowledge base holds HR policy, engineering runbooks, finance forecasts, and security incident reports — that gap is not a minor edge case. It is a fundamental design flaw.

I built Enterprise RAG specifically to treat access control as a first-class retrieval requirement, not an afterthought applied after the answer is generated.

---

## The problem with post-retrieval filtering

The naive approach to document access control in a RAG system is to retrieve first and filter second: score all candidate chunks by relevance, then strip out the ones the user is not allowed to see before generating the answer.

This approach fails in two ways.

**It leaks into the answer.** A generative model given 20 chunks — including 5 restricted ones — can synthesize information from all 20 even if the restricted chunks are stripped from the citation list before the response is returned. The model has already read the finance forecast before you decided not to show it.

**It provides false assurance.** Citation filtering gives the appearance of access control without enforcing it in the part of the pipeline that matters. An audit of the response shows no restricted citations. But the answer content may reflect them.

The correct architecture applies access control before retrieval scoring. Unauthorized chunks are excluded from the candidate set entirely. They are never ranked, never passed to the generator, and never cited.

---

## What silently leaks in a typical internal knowledge base

Consider a company running a single internal knowledge base with documents across four categories:

- **HR and operations** — visible to all employees
- **Engineering runbooks** — visible to engineers and above
- **Finance forecasts and variance reports** — visible to finance team and executives
- **Security incident reports** — visible to engineers and security team

A standard question like "What was the revenue variance in Q3?" asked by an employee role against a system with post-retrieval filtering may return an answer that reflects finance data — even if the finance document does not appear in the citation list. The system retrieved it, scored it, passed it to the generator, and then quietly removed it from the citations.

That is not a hypothetical. It is the predictable behavior of any system where retrieval and access control are separate pipeline stages.

---

## The validation test that most teams do not run

Before I built anything, I defined the evaluation test that the system had to pass:

Ask the same question as two different roles. The answer content and the citation list should differ based on role. If an employee and a finance manager ask "What is the Q3 forecast variance?" and receive answers that contain the same information — regardless of whether the citations differ — the access control is not working.

The evaluation set in Enterprise RAG includes explicit forbidden document IDs per test case. The `restricted_leak_count` metric counts how many evaluation cases returned at least one forbidden document. For a system with correct pre-retrieval access control, that count should be zero.

![Enterprise RAG permission test — same question, different roles, different evidence sets](enterprise-rag-permission-test.png)

The screenshot above shows this test passing: the employee role receives an answer grounded in publicly accessible policy documents, while the finance role receives an answer that additionally cites the restricted finance document. Same question. Different retrieval sets. No leakage.

---

## What this changes operationally

The operational implication is that RAG deployment in an enterprise knowledge base requires a different validation standard than consumer or internal-tooling RAG.

Retrieval relevance is not sufficient. You need:

- A role model that maps document access to user identity
- Pre-retrieval filtering enforced before scoring
- An evaluation set that includes forbidden documents per role, not just expected documents
- A `restricted_leak_count` metric tracked alongside pass rate and citation coverage

Without all four, you cannot know whether your system is leaking restricted content. You can only know whether it is retrieving relevant content — which is a different and less important question in an enterprise security context.

---

## Current limits

- The current implementation uses lexical retrieval with token cosine similarity scoring. Semantic or hybrid retrieval is a planned extension. Lexical retrieval is accurate enough for the validation workflow but does not match production semantic search quality.
- Role metadata is embedded in document front matter. Production deployments should derive role context from Entra ID or an OIDC identity provider, not request body parameters.
- The reference documents are synthetic. The evaluation set is calibrated for repeatable local validation, not a production-scale golden set.
- Multi-tenant isolation is a documented production consideration. The current implementation is single-organization.

---

## Next engineering step

Run `POST /eval/run` against the seeded demo data and check the `restricted_leak_count`. If it is zero, access control is enforced. Then modify the retrieval pipeline to apply scoring before filtering and observe what changes in the evaluation output.

---

## One question for you

If you queried your internal knowledge base with a restricted finance document in the index today, would your evaluation set detect whether that document's content influenced the answer — or only whether it appeared in the citation list?

---

*Next post: The architecture that puts access control before retrieval scoring, and why the order of operations is the entire design.*
