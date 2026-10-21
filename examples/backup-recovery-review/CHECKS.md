# 工程记录

2026-10-21：交付代码、合成样例、Skill、n8n工作流与测试源码；静态AST/JSON/连接和人工逻辑审查，不运行模型、API、工作流或项目测试。真实模型工具轨迹、平台导入、数据库恢复和生产结果均没有实测证据。

## 验收与预期

可手动运行`python -m unittest test_tools.py test_graph.py`，预期13项通过，非实际结果。10项工具测试涵盖样例840秒恢复点落后/1320秒历史服务恢复、900秒与900.1秒边界、等价时区、陈旧清单、无时区、未来证据、倒置时间线、对象越界、备份失败、演练失败。3项脚本模型图测试涵盖工具证据→人工恢复、工具错误纠正和四轮上限；脚本模型不是真实推理验证。

RPO比较只针对记录的恢复点年龄，并要求备份status=completed与清单未陈旧；不验证备份链、日志覆盖、解密材料或一致性。RTO比较针对历史演练的started_at→service_ready_at，非当前事故实测；失败演练不能给出within_target。演练过期、编号不一致、未记录哈希相符分别列缺项。即使所有记录满足，也不声称本次实际可恢复。

工具白名单与system_id严格匹配；模型工具参数错误反馈后继续，畸形响应/网络失败通过API502失败；模型四轮、每消息最多三调用、单次120秒。n8n HTTP等待510秒，无自动重提。成功来源检查仅验证至少一个ID出现，不能证明所有模型语句都有正确证据支持，人工需对照报告。

## 基建逐层选择

| 层级 | 使用或取舍 |
| --- | --- |
| 模型服务 | 已写本机Ollama /api/chat工具协议，固定地址，模型名环境变量；未推理 |
| API契约 | FastAPI/Pydantic严格字段、长度与密钥；带时区参考时间在图初始化检查 |
| 数据与状态 | 合成字典、LangGraph InMemorySaver；无数据库文件，重启丢失状态 |
| Redis缓存/限流 | 暂不需要小样例缓存；串行锁仅单进程忙时429，非按租户限流 |
| 对象存储 | 不读取或上传备份文件，仅元数据；真实存储适配后续另做权限设计 |
| 向量/全文/RAG | 暂不需要，按system_id精确读取结构化资料 |
| 异步队列 | 暂不需要演示；未来长任务需任务身份、队列与过期回收 |
| MCP/适配器 | 三个只读本地函数，无数据库/云备份平台连接；后续接入须限定对象范围 |
| 编排 | LangGraph拥有Agent状态与人工中断，n8n拥有提交/审核转发；Dify与独立LangChain不重复引入 |
| 容器/代理 | 本机单worker，不提供容器部署或公网入口；上线需代理、TLS与身份控制 |
| 观测/评估 | 返回工具轨迹及合成测试源码；未运行测试或持久化审计，不写真实日志 |
| 密钥/身份/审计 | 环境变量密钥及常量时间比较；共享操作员信任范围，reviewer自报，不提供RBAC |
| 幂等/超时/重试 | 有超时和有限循环，无自动重试；提交缺幂等，断网人工先核对任务，不执行任何业务写入 |
| 人工与备份恢复 | 人工仅批准建议；演示本身的检查点未持久化、无备份恢复，不把复核元数据冒充已具备灾备 |

依赖沿用固定顶层版本，传递依赖由安装器解析，未产出全传递锁。恢复点策略15分钟、恢复时长30分钟与演练有效期30天仅为教学业务规则，不是通用标准。

## 官方资料

核查2026-10-21：[PostgreSQL备份分类](https://www.postgresql.org/docs/current/backup.html)、[连续归档与PITR](https://www.postgresql.org/docs/current/continuous-archiving.html)、[LangGraph人工中断](https://docs.langchain.com/oss/python/langgraph/interrupts)、[Ollama工具调用](https://docs.ollama.com/capabilities/tool-calling)、[n8n HTTP Request](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest)。复用invoke/interrupt/Command，不迁移到新流式API。文档核查不构成安装与实机验证。
