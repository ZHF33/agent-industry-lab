# 工程检查：2026-10-30

独立业务场景：数据访问申请的旧批准生命周期分诊；复用既有LangGraph/API/n8n方案。没有补算2026-10-29未完成交付为新项目。本次仅静态审查，不执行测试/模型/平台/课堂代码。直接依赖版本固定，不是全传递依赖锁。

样例as_of=expires_at，阻断approval_expired，execution_authorized=false。14项工具测试源码覆盖到期边界、有效快照仍不授权、范围/修订改变、撤销/已消费、审核者、陈旧、未来、无效区间、拒绝决定、申请身份、工具范围、错误布尔类型；3项脚本图测试覆盖人工恢复、工具错误修正、轮数上限。测试未执行。

模型输出advice_untrusted；source出现不代表全部语义正确。内置批准数据非真实认证；未验证撤销实时性、签名、重放保护或原子消费。本次审批只审建议，不授予业务权限。

| 基建层级 | 选择及边界 |
| --- | --- |
| 模型/推理 | Ollama工具接口、120秒超时；未推理 |
| API契约 | FastAPI/Pydantic严格字段，UUID路径；静态审查 |
| 数据库/状态 | InMemorySaver，重启丢失，无数据库文件；持久审批账本待业务接入 |
| Redis缓存/限流 | 无缓存；单进程忙时429，不是分布式限流 |
| 对象存储 | 小元数据，无文件需求 |
| 向量/全文/RAG | 精确申请身份查表，无检索需求 |
| 异步队列 | 无真实等待任务、回调投递或重试调度，暂不需要队列 |
| MCP/业务适配器 | 三个本地只读白名单工具，无身份/授权系统接入 |
| 编排 | LangGraph循环和人工暂停；n8n转发代码未导入；Dify和独立LangChain适配暂不需要 |
| 容器/反向代理 | 无部署，仅回环单worker |
| 观测评估 | 返回轨迹与报告，合成测试源码；无日志文件或外部观测 |
| 认证密钥/审计 | 环境API密钥、工作流无凭据；缺真实审核者认证/租户绑定/持久审计 |
| 幂等超时/重试 | 有限模型预算/超时；重复提交新线程，无生产幂等；不执行回调重试 |
| 人工审批 | 具名接受/拒绝建议；不续期、不授予访问 |
| 备份恢复 | 内存状态重启需重提；持久状态/消费恢复未实现 |

核查2026-10-30：[Ollama工具调用](https://docs.ollama.com/capabilities/tool-calling)、[LangGraph interrupt](https://docs.langchain.com/oss/python/langgraph/interrupts)、[AWS回调等待](https://docs.aws.amazon.com/step-functions/latest/dg/connect-to-resource.html#connect-wait-token)。AWS仅为外部等待机制参考，本例没有AWS/token接入。详细检查见[当日交付](../../docs/delivery-20261030.md)。
