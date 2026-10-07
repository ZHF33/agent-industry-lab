# Verification — 2026-10-07

Python 3.12; exact tested dependency versions are in requirements.lock.

`python -m pytest -q`: 11 passed. Covers missing/blank facts, mismatched evidence, approval gates, idempotency conflicts, invalid IDs, missing jobs, length limits, persistent decisions after application restart and rejection of decision overwrites.

One third-party deprecation warning remains in Starlette's test client (AnyIO BlockingPortal alias); no test failure.

Local HTTP smoke: health endpoint and POST review tested with synthetic data. Result remains pending human review, semantic_verified=false. No model call, real customer data or publication.

n8n adapter: JSON template supplied, actual target-instance import/execution not yet verified. Dify: integration recipe supplied; no target-instance DSL import or retrieval/model evaluation yet. LangGraph travel Agent: next increment, not implemented in this release. Production auth, backups, monitoring and access controls remain deployment gates.
