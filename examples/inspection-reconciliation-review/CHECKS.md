# 工程记录

2026-11-07。此案例审查计划覆盖和结果基数。组合键为设备与点检项，记录ID用于回查。与按告警事件身份去重的案例分别建模。

| 基建 | 选择及范围 |
| --- | --- |
| 模型 | Ollama 工具调用，单次超时120秒，四轮预算 |
| API | FastAPI/Pydantic 四字段与 UUID 审核路径 |
| 数据库与状态 | 合成字典与内存检查点。持久化与租户隔离待业务接入 |
| Redis | 固定小快照无需缓存，进程忙时429 |
| 对象存储 | 内置小样例，暂无附件 |
| 向量、全文与 RAG | 组合键精确匹配，当前无需知识检索 |
| 队列 | 每表至多100条，同步审查。大规模采集再评估异步作业 |
| MCP 与业务适配 | 三只读工具，暂无设备或工单系统接入 |
| 编排 | LangGraph负责循环和人审，n8n转发。Dify和额外LangChain适配暂无需求 |
| 容器与代理 | 单worker回环8118。生产部署待接入 |
| 观测与评估 | 返回来源和工具轨迹。9项工具测试与3项脚本图测试提供验收源码 |
| 认证与审计 | 环境API密钥，reviewer由调用者填写。强身份与持久审计待接入 |
| 幂等、超时与重试 | 每次提交新线程，模型轮数和超时限制失败范围。无业务写入 |
| 人工审核 | 接受或拒绝报告。release_authorized固定false |
| 备份恢复 | 内存状态重启丢失，持久恢复待接入 |

直接依赖版本固定，传递依赖待目标环境解析。合成快照缺项不能证明实际点检未进行。多条记录可能是复测，当前保留全部来源，由人工解释。版本与时效只标记限制，不将证据升级为设备放行依据。

实际范围为 AST、JSON、链接、工作流连接和 Git 差异。测试、模型、平台及课堂示例待运行验收。无真实模型轨迹。工作流 inactive，凭据由使用者配置。

2026-11-07 核查 PostgreSQL 的 EXISTS/NOT IN 条件、Ollama 工具回传、LangGraph 检查点与中断。实际对账采用 Python 集合与分组，数据库实现属于教学对照。 [PostgreSQL](https://www.postgresql.org/docs/current/functions-subquery.html) · [Ollama](https://docs.ollama.com/capabilities/tool-calling) · [LangGraph](https://docs.langchain.com/oss/python/langgraph/interrupts)
