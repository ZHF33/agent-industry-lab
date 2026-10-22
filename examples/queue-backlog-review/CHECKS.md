# 工程检查与验收设计

2026-10-22交付：源码、合成遥测、LangGraph/FastAPI/n8n、Skill与13项可选测试源码。默认仅静态AST/JSON/链接及人工逻辑审查；未执行模型、API、n8n、测试或课程示例，没有真实模型轨迹、消息代理或生产验收。

## 口径与预期

`python -m unittest test_tools.py test_graph.py`预期13项通过，非实际结果。10项工具测试涵盖样例、计数矛盾、陈旧快照、零确认、零消费者、布尔值伪整数、未来资料、无时区、对象越界及零时间窗。3项脚本模型控制测试覆盖工具→人工恢复、错误工具纠正和轮数耗尽。

样例区间300秒，total_start=120，total_end=300；600发布-420确认=180，与总量增长一致。published_per_second=2、acked_per_second=1.4、零新增情景214.29秒。陈旧或矛盾时估计为null。Decimal用于率与情景除法，不舍入计数。ready与unacked之间的投递转移不改变两者总量。

仅适用本合成窗口契约：同一队列代际，accepted publish/ack计数，无重试、重置、未知移出路径。expired/purged/dead_lettered_out为互不重叠移出项，真实遥测未必满足；接入前需定义每个计数的范围和采集一致性。worker错误是相关证据，未验证根因、业务成功或重复副作用。

模型四轮/每消息三工具/每次120秒，n8n等待510秒，无自动重试；工具错误可在预算内纠正，网络或畸形回复API502失败。引用检查仅确认至少一个精确ID出现，不验证模型每句话，人工需对照工具报告。

## 基建评估

| 层级 | 选择与边界 |
| --- | --- |
| 模型服务 | Ollama /api/chat适配源码，固定本机地址/可配置模型名，未推理 |
| API契约 | FastAPI/Pydantic严格字段、长度、密钥；时间在图初始化检查 |
| 数据状态 | 合成字典与InMemorySaver；无数据库文件，重启丢失 |
| Redis缓存/限流 | 暂不需要遥测缓存；单进程锁繁忙429，不是按用户限流 |
| 对象存储 | 暂不需要，只有小型合成计数，不处理消息附件 |
| 检索/RAG | 暂不需要，queue_id精确读取，无全文/向量语料 |
| 异步队列 | 业务主题涉及队列，但工具只分析遥测，未接RabbitMQ/Redis/Celery；Agent本身同步运行 |
| MCP/适配器 | 三个只读函数，无真实代理、监控或业务系统连接；后续需最小权限适配器 |
| 编排 | LangGraph负责自主工具和人工恢复，n8n仅入口/转发；Dify与独立LangChain无重复编排需求 |
| 容器/代理 | 本机单worker，未提供容器/反向代理部署；公网需TLS和身份系统 |
| 观测/评估 | 返回轨迹、有限合成测试源码；未执行评估或持久审计，不存运行日志 |
| 认证/密钥 | 环境变量共享密钥、对象白名单；无多租户授权，reviewer自报 |
| 幂等/超时/重试 | 有预算与超时，无自动重提或业务动作；提交未做幂等 |
| 人工/备份恢复 | 仅复核建议，不操作队列；内存检查点无持久备份恢复 |

顶层依赖沿用固定版本；未生成完整传递依赖锁。未知对象拒绝；代码禁止读取真实业务数据。源码MIT，依赖/模型许可独立保留。

## 官方核查

2026-10-22阅读：[RabbitMQ队列](https://www.rabbitmq.com/docs/queues)、[确认与发布确认](https://www.rabbitmq.com/docs/confirms)、[LangGraph人工中断](https://docs.langchain.com/oss/python/langgraph/interrupts)、[Ollama工具调用](https://docs.ollama.com/capabilities/tool-calling)。这些资料用于机制与沿用接口核查，不能据此宣称接入了RabbitMQ或平台已运行。
