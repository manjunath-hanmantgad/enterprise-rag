# Walkthrough

This walkthrough validates secure retrieval, citation quality, access control, key revocation, and evaluation metrics.

1. Show the architecture diagram.
2. Ingest the reference documents.
3. Create a local finance user and API key.
4. Ask a finance forecast question with no key as `employee` and show no finance citation appears.
5. Ask the same finance question with the finance API key and show the finance citation appears.
6. Revoke the API key and show that the key is rejected.
7. Ask an incident response question as `engineer`.
8. Run evaluation and show `restricted_leak_count` is zero.

Screenshot set:

- dashboard overview
- citation-backed answer
- permission contrast between employee and finance roles
- evaluation summary

Current assets:

- `demo/enterprise-rag-dashboard.png`
- `demo/enterprise-rag-citations.png`
- `demo/enterprise-rag-permission-test.png`
- `demo/enterprise-rag-evaluation.png`
