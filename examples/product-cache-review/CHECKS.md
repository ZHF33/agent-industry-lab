# 工程检查与基建选择

2026-10-24：静态AST/JSON/链接及人工逻辑审查。未运行Ollama、API、n8n或测试，没有模型轨迹、Redis实机或生产证据。顶层依赖固定，未生成完整传递依赖锁。

## 验收设计

手动`python -m unittest test_tools.py test_graph.py`预期13项通过，非实际结果。10项工具测试覆盖正TTL仍版本/价格不符、缺键、无过期、零TTL、旧证据、币种/身份错配、NaN、无时区/未来、越界对象；3项脚本模型测试覆盖人工恢复、错误工具纠正、四轮上限。脚本模型不是实机模型验证。

工具比对两份合成快照，不读取真实键。TTL从cache观测时刻向参考时刻线性投影，忽略期间刷新/删除/淘汰，故实时presence始终unknown。版本只比相等；金额用Decimal，拒绝负值/非有限值/超两位小数。陈旧证据或产品错配不算价差，币种不同不跨币种相减。确认实际收费需要另一权威证据，当前不提供。

API四轮/每消息三工具/单次120秒；n8n等待510秒，无自动重试。工具参数错误返回模型纠正，网络/畸形响应API502。至少一个来源ID检查不能证明每句模型建议正确，人工需核实。

| 层级 | 实现、取舍与未验证范围 |
| --- | --- |
| 模型 | Ollama /api/chat适配源码，固定本机、环境变量模型；未推理 |
| API契约 | FastAPI/Pydantic严格字段、长度、密钥，时间在图初始化检查 |
| 数据状态 | 合成字典/内存检查点；无数据库，重启丢失 |
| Redis缓存/限流 | 仅TTL元数据分析，未接Redis；单进程锁忙时429，不是按用户限流 |
| 对象存储 | 暂不需要小记录无附件 |
| 检索/RAG | 暂不需要结构化product_id查询，无全文或向量 |
| 队列 | 暂不需要本地演示；真正失效事件可另接队列，但不在本例 |
| MCP/适配器 | 三只读函数，未接真实商品、Redis、CDN、结算API |
| 编排 | LangGraph为唯一Agent循环，n8n仅入口/审核转发；不重复Dify/独立LangChain |
| 容器/代理 | 本机单worker，暂不部署；公网需TLS/代理/身份系统 |
| 观测/评估 | 响应内轨迹、合成测试源码，无实测/持久审计 |
| 认证/密钥 | 环境变量共享密钥与对象范围；reviewer自报，无租户隔离 |
| 幂等/超时/重试 | 超时、预算、无自动重提；提交未做幂等，无业务写入 |
| 人工/备份恢复 | 只批建议，内存检查点无持久备份恢复，清缓存另需授权工具 |

官方核查2026-10-24：[Redis TTL](https://redis.io/docs/latest/commands/ttl/)、[EXPIRE](https://redis.io/docs/latest/commands/expire/)、[LangGraph中断](https://docs.langchain.com/oss/python/langgraph/interrupts)、[Ollama工具](https://docs.ollama.com/capabilities/tool-calling)。Redis资料用于TTL语义，不构成集成验证。保留MIT与第三方依赖/模型许可。
