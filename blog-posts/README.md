# Enterprise RAG — Blog Post Series

6-post series for Medium / Substack. Each post is standalone. Together they form a complete practitioner case study.

**Tone:** First-person engineering retrospective. Not a tutorial. Not a product pitch.
**Target:** Mixed — Engineering leaders (CTO, EM) + practitioners (Staff Eng, MLOps, Platform Eng, Security Eng).

---

## Series Arc

| File | Post title | Pillar |
|---|---|---|
| `01-the-access-control-gap-in-enterprise-rag.md` | The Access Control Gap That Makes Most Enterprise RAG Systems Dangerous | Problem and failure mode |
| `02-architecture-retrieval-before-scoring.md` | How Enterprise RAG Is Structured: Why Access Control Comes Before Retrieval Scoring | Architecture and boundaries |
| `03-design-decisions-retrieval-pipeline.md` | Three Design Decisions That Shaped the Enterprise RAG Retrieval Pipeline | Design decisions (why A over B) |
| `04-evaluation-metrics-that-matter.md` | Four Metrics That Actually Tell You Whether Your Enterprise RAG Is Working | Validation and measured outputs |
| `05-security-controls-api-keys-audit-logs.md` | Security Controls in Enterprise RAG: Keys, Audit Logs, and the Hierarchy That Prevents Role Elevation | Security and controls |
| `06-deployment-readiness-and-limits.md` | What Enterprise RAG Is Ready For Today and What Production Deployment Actually Requires | Deployment readiness and limits |

---

## Screenshots for Medium upload

Source files are in `../demo/`. Upload each PNG directly via Medium's inline image button.
Use the alt text in each post as the Medium caption.

| Screenshot | Used in posts |
|---|---|
| `enterprise-rag-permission-test.png` | 1 |
| `enterprise-rag-dashboard.png` | 2 |
| `enterprise-rag-evaluation.png` | 4 |
| `enterprise-rag-citations.png` | 4 |

## Medium publishing checklist

Before hitting Publish on each post:
- [ ] Upload referenced screenshots inline at the correct position
- [ ] Replace the `*Post N of 6*` series line with a Medium series tag if applicable
- [ ] In post 6, fill in the series index with actual Medium post URLs after earlier posts are published
- [ ] Add Medium tags: `rag`, `enterprise-ai`, `machine-learning`, `software-engineering`, `information-retrieval`
- [ ] Set subtitle from the first sentence of each post's opening paragraph

## QA checklist status

All 6 posts verified against the playbook QA checklist:
- Every claim maps to a verified file, endpoint, or screenshot
- No unverifiable metrics included (no percentage improvement claims)
- "Production" wording is scoped precisely throughout
- Security claims are specific: "SHA-256 hash", "pre-retrieval role filter", "ADMIN_TOKEN required"
- At least one limitation disclosed per post
- One technical anchor per post (API path, architecture component, or metric)
- No full code blocks or replication walkthroughs
- No hype terms used
