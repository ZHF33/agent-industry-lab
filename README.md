# Agent Industry Lab

**JOJO's practical Agents, reusable Skills, and business workflows.**

一个持续实现的工程系列：场景 → 工作流 → 可运行代码 → 验收证据。

| Case | Stack | Verified scope |
| --- | --- | --- |
| [Bakery Agent source](examples/bakery-agent/README.md) | Dify, n8n, Python API, SQLite | Portable core source + synthetic fixtures; local demo verified |
| [Agentic-VSDR](docs/existing-agents.md#agentic-vsdr) | Vision-language diagnosis, restoration tools | Existing research simulation; real-model evaluation separate |
| [Bakery Content Review Skill](examples/bakery-review/README.md) | FastAPI, SQLite, structured evidence, n8n adapter | Local API implementation; see verification report |
| [Product Cache Review](examples/product-cache-review/README.md) | LangGraph, n8n, FastAPI | TTL, authoritative version and price evidence, human review |
| [Queue Backlog Review](examples/queue-backlog-review/README.md) | LangGraph, n8n, FastAPI | Ready/unacked balance, throughput evidence, human review |
| [Backup Recovery Review](examples/backup-recovery-review/README.md) | LangGraph, n8n, FastAPI | Recovery point, restore-drill evidence, human review |
| [Certificate Renewal Review](examples/certificate-renewal-review/README.md) | LangGraph, n8n, FastAPI, datetime | Certificate inventory expiry, deployment evidence, human review |
| [Alert Noise Review](examples/alert-noise-review/README.md) | LangGraph, n8n, FastAPI, Counter | Duplicate deliveries, conflict evidence, human review |
| [API Failure Triage](examples/api-failure-triage/README.md) | LangGraph, n8n, FastAPI | Failure evidence, uncertain outcomes, human review |
| [Network Access Review](examples/network-access-review/README.md) | LangGraph, n8n, FastAPI, ipaddress | Synthetic access policy checks, human review |
| [Invoice Three-Way Match](examples/invoice-three-way-match/README.md) | LangGraph, n8n, FastAPI, Decimal | Order/receipt/invoice reconciliation, human review |
| [Sensor Data Quality](examples/sensor-data-quality/README.md) | LangGraph, n8n, FastAPI | Freshness, range and unit checks, human review |
| [Return Evidence Review](examples/return-evidence-review/README.md) | LangGraph, n8n, FastAPI | Return evidence, quantity and date checks, human review |
| [Release Artifact Review](examples/release-artifact-review/README.md) | LangGraph, n8n, FastAPI, SHA-256 | Manifest/artifact comparison, integrity evidence, human review |
| [Shipment Delay Investigation](examples/shipment-delay/README.md) | LangGraph, n8n, FastAPI, datetime | Timezone-aware delay assessment, evidence review, human approval |
| [Supplier Quote Review Agent](examples/supplier-quote-review/README.md) | LangGraph, n8n, FastAPI, Decimal | Quote cost comparison, delivery checks, human review |
| [Inventory Discrepancy Agent](examples/inventory-discrepancy/README.md) | LangGraph, n8n, FastAPI, Ollama | Stock/count investigation, exact difference tool, human review |
| [Maintenance Ticket Triage](examples/maintenance-triage/README.md) | LangGraph, n8n HTTP workflow, local Ollama Qwen3 | Real model: 3 tools, 3 rounds; 8 control tests; human review |
| [Travel Document Triage](examples/travel-triage/README.md) | Python, optional local Ollama tools | Rule prototype: 16 tests + 12 synthetic cases; real model unverified |

## 从零到一学大模型

**零基础中文教学 · 365个学习单元 · 从认识模型到交付行业应用。**

[课程发布页](llm-zero-to-one/README.md) · [365天完整计划](llm-zero-to-one/PLAN-365.md) · [第一期：大模型到底是什么？](llm-zero-to-one/lessons/day-001.md) · [第二期：模型与聊天产品](llm-zero-to-one/lessons/day-002.md) · [第三期：训练与使用](llm-zero-to-one/lessons/day-003.md) · [第四期：参数与资料库](llm-zero-to-one/lessons/day-004.md) · [参考课程拆解](llm-zero-to-one/SOURCES.md)

从Python与接口基础进入RAG、Agent、微调、推理优化和可靠性；每天配讲解、练习与交付要求。参考Datawhale与Maxime Labonne开源课程，独立编排原创案例。计划与已发布正文分别列出。

## 基建知识库

[每日基建拆解](knowledge-base/README.md)：业务问题、原理、最小示例、验证与选型。首篇：[幂等、事务与重试](knowledge-base/01-idempotency.md)。

项目基建评估使用[选型清单](docs/infrastructure-checklist.md)，覆盖模型、数据、检索、队列、工具、部署、观测、安全与恢复；按需采用。

最新基建课：[消息队列与确认](knowledge-base/15-queues-and-acknowledgements.md)。

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

## License and policies

Original repository code and documentation are available under [MIT](LICENSE). External dependencies, model weights and service terms retain their own licenses; MIT does not grant rights to third-party trademarks or private data.

[Contributing](CONTRIBUTING.md) · [Security policy](SECURITY.md)
