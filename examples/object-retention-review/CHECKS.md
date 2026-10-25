# 工程记录：2026-10-25

范围：沿用现有已批准的LangGraph工具循环、FastAPI和n8n转发架构，新增对象版本/保留的独立场景。静态检查命令与结果见docs/delivery-20261025.md。没有执行测试、模型推理、平台导入或存储操作。

## 逻辑审查与预期

- 十二项工具边界测试：删除标记与旧版限制、过期不授权、hold、陈旧、不完整、缺项、版本错配、重复版本、跨对象、无时区、未来时间、对象身份错配。
- 三项脚本化图测试：人工暂停/恢复、工具错误修正、轮数上限。脚本化模型不是实际模型验证。
- 样例预期：delete_marker；data-v1 restriction_recorded；deletion_authorized=false；actions_executed=false。
- 模型最多4轮、每轮3工具，HTTP模型超时120秒，无自动业务重试。失败可能抛502，不伪造建议。
- 依赖固定直接版本；未生成完整传递依赖锁或做依赖兼容实机验证。
- 引用存在不代表模型推理正确；建议字段标advice_untrusted，确定性报告和人工复核保留。

## 全层基建评估

| 能力 | 当前选择与边界 |
| --- | --- |
| 模型/推理 | Ollama工具调用接口代码；模型版本由使用者配置，实机未验 |
| API契约 | FastAPI/Pydantic严格字段、UUID、X-API-Key；静态审查 |
| 数据库/状态 | InMemorySaver；无数据库，重启丢失；持久化列后续需求 |
| Redis/限流 | 无缓存；单进程锁忙时429，非分布式限流 |
| 对象存储 | 本例主题，仅内置合成版本元数据；不接S3、不读取对象 |
| 向量/全文/RAG | 结构化对象身份直查，无检索库需求 |
| 队列 | 同步短MVP无异步队列；长任务生产需另设计 |
| MCP/适配器 | 白名单本地工具；真实存储只读适配器尚未实现 |
| 编排 | LangGraph循环与审批；n8n仅入口转发，未实机导入；Dify暂不需要；LangChain独立适配暂不需要 |
| 容器/反代 | 本地回环地址、单worker；不发布容器或公网服务 |
| 观测/评估 | 返回内存轨迹；合成测试源码，未执行；不保存运行日志 |
| 认证/密钥/审计 | 环境变量密钥、凭据不入工作流；缺租户权限与持久审计 |
| 幂等/超时/重试 | UUID线程、并发拒绝、有限轮数、超时；提交重复会创建新线程，无生产幂等保证 |
| 人工审批 | interrupt/Command；只审建议，不能授权真实操作 |
| 备份恢复 | 无持久状态，重启后需重新提交；对象版本不等于独立备份 |

## 官方接口资料

2026-10-25核查：[LangGraph interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)、[Ollama工具调用](https://docs.ollama.com/capabilities/tool-calling)、[S3删除标记](https://docs.aws.amazon.com/AmazonS3/latest/userguide/DeleteMarker.html)、[S3 Object Lock](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html)。本例只表达合成固定保留期限/法律保留元数据，不复现云端完整授权、合规模式或全部保留类型。

工作流复核路径仅接受UUID形状，其他值转invalid-thread由API拒绝，避免把任意路径拼入请求。n8n HTTP参数核查：[HTTP Request官方文档](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/)。
