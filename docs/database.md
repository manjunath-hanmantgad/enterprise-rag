# Database

Local mode uses SQLite at `RAG_DATABASE_PATH`. Managed deployments can use PostgreSQL-compatible storage through `STORAGE_BACKEND=postgres` or `STORAGE_BACKEND=azure_postgres` and `DATABASE_URL`.

The application initializes the same logical schema for SQLite and PostgreSQL. SQLite is intended for local development and repeatable validation. PostgreSQL or Azure Database for PostgreSQL should be used for cloud deployments that need backups, high availability, connection monitoring, and managed patching.

## Configuration

SQLite:

```env
STORAGE_BACKEND=sqlite
RAG_DATABASE_PATH=storage/enterprise_rag.db
```

PostgreSQL or Azure Database for PostgreSQL:

```env
STORAGE_BACKEND=azure_postgres
DATABASE_URL=postgresql://user:password@host:5432/enterprise_rag?sslmode=require
```

The live integration verifier opens the configured database, initializes the schema, and runs a simple connectivity query when `DATABASE_URL` is provided.

## Tables

`documents`

- `id`
- `title`
- `department`
- `allowed_roles`
- `source_path`
- `checksum`
- `created_at`

`chunks`

- `id`
- `document_id`
- `chunk_index`
- `content`
- `allowed_roles`

`users`

- `username`
- `full_name`
- `role`
- `password_hash`
- `created_at`

`api_keys`

- `user_id`
- `name`
- `key_prefix`
- `key_hash`
- `revoked_at`
- `created_at`

`query_logs`

- `question`
- `user_role`
- `answer`
- `citations_json`
- `latency_ms`
- `retrieved_count`
- `blocked_count`

`evaluation_runs`

- `total_cases`
- `pass_count`
- `restricted_leak_count`
- `citation_coverage`
- `average_latency_ms`

`audit_logs`

- `action`
- `actor`
- `detail`
- `created_at`

## Production Notes

- Use managed PostgreSQL credentials from Azure Key Vault or the hosting platform secret store.
- Keep `DATABASE_URL` out of source control and public screenshots.
- Enable TLS to the managed database. For Azure Database for PostgreSQL, use `sslmode=require`.
- Use platform backups and point-in-time restore for production environments.
- Use connection limits appropriate for the hosting tier. For high traffic, add a managed pooler or platform-supported pooling layer.
