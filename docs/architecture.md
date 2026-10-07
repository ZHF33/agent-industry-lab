# Architecture and engineering gates

Business trigger (n8n) → validated request + idempotent job ID → case API → Dify workflow or LangGraph orchestration → durable review report → human decision → separately authorized business action.

The first Skill runs deterministic evidence checks. It never claims semantic verification. A future Dify workflow extracts structured claims with citations; the Skill checks evidence references and a human checks complete copy. LangGraph is used for actual autonomous multi-step tools and checkpointed approvals, not added to a deterministic validator.

Local case state uses SQLite. Production Agent state targets PostgreSQL checkpointers. Scale n8n to Redis/PostgreSQL queue mode only after measured concurrency needs. Retry transient operations with limits; permanent validation failures terminate; idempotency guards repeated inputs; revisions use new IDs.

RAG: versioned sources, chunking by document structure, metadata isolation, hybrid retrieval when measured beneficial, optional reranking, source citations and retrieval regression tests. Retrieved text is evidence, not instructions. No ungrounded answer passes as verified.

Version policy: lock tested non-prerelease dependencies; verify target n8n/Dify import compatibility against installed versions. Record model, prompt, retrieval corpus and evaluation results separately. Backups, retention, auth, monitoring and restoration drills are production gates.

References checked 2026-10-07:
- https://docs.langchain.com/oss/python/langgraph/persistence
- https://docs.n8n.io/hosting/scaling/queue-mode/
- https://www.dify.ai/rag
