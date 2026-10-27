# 2026-10-27 工程检查

沿用既有LangGraph受控循环/FastAPI/n8n提交与审批方案，独立实现API批量同步配额审查。仅静态检查，不执行测试、模型、平台、课堂代码或业务请求。依赖固定直接版本，未做传递依赖锁及实机兼容验证。

## 预期与逻辑

样例：3+2×2.5=8令牌；批次11大于容量10，outcome=batch_exceeds_capacity，ideal_wait_seconds=null。若改批次9，理想等待1/2秒；仅是无竞争投影，不是实际可重试保证。14个工具测试源码涵盖样例、精确等待、封顶、零补充、等值边界、陈旧、版本/对象错配、未来、超容量初始令牌、负速率、bool输入、工具范围和无时区；3个脚本图测试覆盖审批恢复、错误修正、轮数上限。

引用ID检查不验证自然语言全部结论；人工复核仍必需。固定配置与无其他消费者是模型前提；未知消费、配置变更、多个网关、并发和队列都不在投影中。原子批次定义为本例全部一起准入，不代表普通HTTP请求天然按批次原子处理。

## 全层基建评估

| 能力 | 选择与边界 |
| --- | --- |
| 模型接入/推理 | Ollama接口代码、120秒超时；未实机推理 |
| API数据契约 | FastAPI/Pydantic严格字段，UUID审批；单worker回环地址 |
| 数据库/状态 | InMemorySaver；不持久化、不上传数据库，重启丢失 |
| Redis/限流 | 不接Redis；工具只是快照投影，API忙时429是单进程锁，不是令牌桶 |
| 对象存储 | 小合成计数，无文件/对象需求 |
| 向量/全文/RAG | 精确身份查配置，暂不需要检索 |
| 异步队列 | 无真实重试或调度，暂不需要队列；长任务另设计 |
| MCP/业务适配器 | 三个白名单本地工具；无外部网关连接 |
| 编排 | LangGraph状态/审批；n8n转发代码未导入；Dify/LangChain额外适配暂不需要 |
| 容器/反代 | 不部署服务、不提供公网入口 |
| 观测评估 | 返回工具轨迹；合成测试源码未执行，无运行日志 |
| 认证密钥/审计 | 环境变量API密钥，工作流无凭据；缺租户身份绑定和持久审计 |
| 幂等/超时/重试 | UUID、有限工具预算/模型超时；重复提交新线程，没生产幂等；不自动重试 |
| 人工审批 | 仅接受/拒绝建议，不发送请求或改配置 |
| 备份恢复 | 无持久状态，重启后需重提；正式状态备份另做 |

## 官方资料

2026-10-27核查：[Ollama工具调用](https://docs.ollama.com/capabilities/tool-calling)、[LangGraph interrupt](https://docs.langchain.com/oss/python/langgraph/interrupts)、[API Gateway限流](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-request-throttling.html)、[Fraction](https://docs.python.org/3/library/fractions.html)。API Gateway为令牌桶机制参考，本例未接AWS，不能推断云服务保证。检查记录见[当日交付](../../docs/delivery-20261027.md)。
