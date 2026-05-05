# Evaluation

Evaluation cases live in `demo/evaluation_set.json`.

Each case defines:

- `question`
- `user_role`
- expected document ids
- forbidden document ids

Metrics:

- `pass_rate`: expected documents were retrieved and forbidden documents were not.
- `restricted_leak_count`: number of cases that returned at least one forbidden document.
- `citation_coverage`: average citation count per case.
- `average_latency_ms`: average query latency across cases.

Run locally:

```bash
curl -X POST http://127.0.0.1:8002/eval/run
```

The included evaluation set is deterministic and optimized for repeatable access-control and citation checks. Production teams can extend it with larger golden sets, human relevance labels, answer correctness checks, and regression thresholds in CI.
