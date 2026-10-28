# 工程检查：2026-10-28

沿用既有LangGraph工具循环/API/n8n人工审核方案，新增工单修订冲突独立场景。仅静态检查；没有执行测试、模型、平台、业务操作或课堂脚本。直接依赖固定版本，不是完整传递锁。

## 预期与边界

样例base_revision=4、observed_revision=5，status=revision_conflict；actions_executed/write_authorized/atomic_write_verified均false。12项工具测试源码覆盖冲突、相同版本仍不授权、缺基准、关闭工单、身份、陈旧、未来、bool版本、越字段修改、工具范围、无时区和超前基准。3个脚本图测试覆盖暂停恢复、工具修正和轮数上限。均未执行。

所有结果仅基于快照；相同版本不消除读取至执行间的竞争。没有CAS、事务、ETag或真实业务适配。模型引用校验只检查ID，不证明全部文本正确。人工须核对重新获取的业务记录；本例approve只审建议。

## 全层基础设施评估

| 层级 | 选择与后续边界 |
| --- | --- |
| 模型/推理 | Ollama接口代码，120秒超时；未实机执行 |
| API契约 | FastAPI/Pydantic严格字段，UUID审核，回环单worker |
| 数据库/状态 | InMemorySaver；无数据库文件，不持久化；真实CAS待业务适配设计 |
| Redis/限流 | 无缓存需求；单进程忙时429，不是分布式限流 |
| 对象存储 | 小合成记录，无上传文件需求 |
| 向量/全文/RAG | 对象身份精确查找，无检索需求 |
| 异步队列 | 同步MVP，无派单/写任务，无队列 |
| MCP/业务适配器 | 白名单内置只读工具，工单业务接口未接 |
| 编排 | LangGraph循环/interrupt；n8n转发代码未导入；Dify和独立LangChain适配暂不需要 |
| 容器/反代 | 无部署，不直接公开服务 |
| 观测评估 | 返回轨迹、确定性报告、测试源码；无外部观测或运行日志 |
| 认证密钥/审计 | 环境API密钥，工作流不嵌凭据；缺租户身份绑定与持久审计 |
| 幂等超时/重试 | 有限轮数/超时，重复提交新线程；无真实写重试，不保证生产幂等 |
| 人工审批 | 接受/拒绝建议；不赋予编辑/派单权限 |
| 备份恢复 | 内存重启需重提；正式状态持久化/备份待需求 |

## 官方来源

2026-10-28核查：[Ollama工具调用](https://docs.ollama.com/capabilities/tool-calling)、[LangGraph interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)、[RFC 9110 If-Match](https://www.rfc-editor.org/rfc/rfc9110.html#name-if-match)、[PostgreSQL事务隔离](https://www.postgresql.org/docs/current/transaction-iso.html)。后两者仅用于说明实际写端应有条件检查，不代表本Agent已接入或实现。完整静态范围见[当日交付](../../docs/delivery-20261028.md)。
