# Retrieval

The default implementation uses deterministic lexical retrieval so local validation can run without API keys or vector services.

Configured by:

```env
RAG_RETRIEVAL_PROVIDER=local
```

Supported provider values:

- `local`: implemented deterministic lexical retrieval.
- `openai`: reserved for an embedding-backed vector retrieval configuration.
- `azure_ai_search`: implemented REST adapter for Azure AI Search document search.

Pipeline:

1. Parse markdown metadata.
2. Chunk document body text.
3. Store document and chunk records in SQLite.
4. Load candidate chunks for a query.
5. Apply role filtering before scoring.
6. Score accessible chunks with token cosine similarity.
7. Return top citations and retrieval metrics.

The important enterprise behavior is the order of operations: access control is applied before retrieval scoring. Unauthorized chunks are not ranked, cited, or sent to the answer generator.

Azure AI Search mode expects an index with these retrievable fields:

- `chunk_id`
- `document_id`
- `title`
- `content`
- `allowed_roles`

It applies an ACL filter before results are returned:

```text
allowed_roles/any(role: role eq 'all' or role eq '<user_role>')
```

Planned retrieval extensions:

- OpenAI embeddings plus a local vector index
- Azure AI Search vector or hybrid query support
- document-level and section-level ACLs
- semantic reranking
- freshness and source-priority scoring

When a non-local retrieval provider is selected, the application validates required credentials and fails with a clear configuration error instead of silently falling back to local retrieval.
