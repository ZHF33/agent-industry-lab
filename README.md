# Agent Industry Lab

**JOJO's practical Agents, reusable Skills, and business workflows.**

一个持续实现的工程系列：场景 → 工作流 → 可运行代码 → 验收证据。

| Case | Stack | Verified scope |
| --- | --- | --- |
| [Bakery Agent source](examples/bakery-agent/README.md) | Dify, n8n, Python API, SQLite | Portable core source + synthetic fixtures; local demo verified |
| [Agentic-VSDR](docs/existing-agents.md#agentic-vsdr) | Vision-language diagnosis, restoration tools | Existing research simulation; real-model evaluation separate |
| [Bakery Content Review Skill](examples/bakery-review/README.md) | FastAPI, SQLite, structured evidence, n8n adapter | Local API implementation; see verification report |
| [Travel Document Triage](examples/travel-triage/README.md) | Python, optional local Ollama tools | Rule prototype: 16 tests + 12 synthetic cases; real model unverified |

## Run the first Skill

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m uvicorn industry_lab.api:app_factory --factory --host 127.0.0.1 --port 8091
```

API docs: http://127.0.0.1:8091/docs. Local demonstration only: authentication and network hardening must precede exposure to other users. Approval records never publish business content.

## Engineering approach

n8n handles business triggers and integration. Dify handles editable workflows and knowledge. LangChain/LangGraph handles model tools and durable Agent state where needed. RAG requires source attribution, retrieval evaluation and insufficient-evidence handling. Each case chooses its orchestration owner; all technologies are not forced into every example.

Daily work finishes a runnable increment and continues unfinished integrations before opening another case. Status levels: implemented → offline verified → model verified → platform verified → production operated. Templates alone do not count as platform verification.

Next: real n8n execution, Dify knowledge integration, then real-model verification of the travel-document triage prototype. No real customer records or credentials are included.

[Architecture](docs/architecture.md) · [Verification](docs/verification.md) · [JOJO](https://github.com/ZHF33)
