# Public Release Guide

Use this guide when preparing `02-enterprise-rag` as a standalone public repository.

## Include

- `README.md`
- `docs/`
- `demo/README.md`
- fictional demo documents
- screenshot assets in `demo/`
- `.env.example`
- source code
- tests
- `requirements.txt`
- `pyproject.toml`
- Docker files
- `.github/workflows/ci.yml`

## Exclude

- `.env`
- `.venv/`
- `storage/*.db`
- generated caches
- internal workspace planning files
- social-media planning files
- graph output
- issue history unless intentionally converted into public release notes

## Validation

Before publishing:

1. Run tests.
2. Start the API from README commands.
3. Run demo ingestion.
4. Verify `/query`, `/metrics`, and `/eval/run`.
5. Capture or refresh current screenshots.
6. Confirm `.env.example` contains placeholders only.
7. Confirm documentation does not reference internal workspace strategy.
8. Confirm CI passes after pushing the standalone repository.

Prepare and validate a standalone artifact:

```bash
.venv/bin/python scripts/prepare_public_release.py --destination /private/tmp/enterprise-rag-public
```

The script copies public files, excludes local databases and internal docs, checks required files, and scans text files for common secret patterns.

See `docs/production-readiness.md` for the current release status and remaining production gaps.
