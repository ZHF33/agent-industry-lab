# 工程记录

2026-11-06。新案例处理生产任务前置约束，使用标准库TopologicalSorter与合成状态快照。与批次追溯的下游可达性问题分别建模。

| 层级 | 选择和边界 |
| --- | --- |
| 模型接入 | Ollama工具调用源码，120秒超时、四轮预算，未实机推理 |
| API契约 | FastAPI/Pydantic四字段和UUID审核路径，任务ID/状态/前置列表校验 |
| 数据库状态 | 合成字典、内存检查点，重启需重提。持久化和租户隔离待业务接入 |
| Redis缓存限流 | 小快照无需缓存。单进程忙时429 |
| 对象存储 | 无附件归档，暂不需要 |
| 向量/全文/RAG | 计划ID精确查询，暂无检索需求 |
| 异步队列 | 最多100任务/500依赖，固定小分析。真实执行调度另行设计 |
| MCP/业务适配器 | 三只读本地工具，未接MES或设备系统 |
| 编排 | LangGraph循环和人审，n8n转发源码。Dify知识运营和独立LangChain适配暂无需求 |
| 容器/代理 | 单worker回环8117，生产部署待接入 |
| 观测评估 | 返回来源、工具轨迹及结构结果，持久日志/外部观测待接入 |
| 认证密钥审计 | 环境API密钥，审核者文字由调用方填写，强身份和持久审计待接入 |
| 幂等超时重试 | 每次提交新线程，预算/超时限制模型失败范围，无业务写入或自动重试 |
| 人工审批 | 接受/拒绝分析，dispatch_authorized固定false |
| 备份恢复 | 内存状态丢失后重新提交，持久恢复待业务接入 |

12项工具测试和3项脚本图测试源码，实际仅做AST/JSON/Markdown链接围栏、工具范围/预算、工作流接线和Git差异检查。未执行测试、模型、API、平台或课堂脚本，无真实模型工具轨迹。

依赖固定直接版本，传递锁待目标环境解析。结构顺序不是资源排程；前置全部done也不授予派工权限。任意循环使本例全局候选为空，即使有其他独立分支。CycleError仅给一个循环示例，不枚举全部环。状态自洽仍需可信来源与实时执行检查。

2026-11-06核查官方接口的前置列表方向、static_order与CycleError，以及模型工具回传和interrupt检查点职责。工作流保持inactive，凭据由使用者配置。MIT与第三方许可保留。 [Python graphlib](https://docs.python.org/3/library/graphlib.html) · [Ollama](https://docs.ollama.com/capabilities/tool-calling) · [LangGraph](https://docs.langchain.com/oss/python/langgraph/interrupts)
