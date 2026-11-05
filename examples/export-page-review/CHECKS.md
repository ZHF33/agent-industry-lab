# 工程记录

2026-11-05。分页订单导出审查基于合成快照，检查游标链、唯一ID和显式结束。真实导出采集、订单修改和导入未接入。

| 基建 | 选择及范围 |
| --- | --- |
| 模型服务 | Ollama工具接口源码，120秒超时、四轮预算，未实机推理 |
| API契约 | FastAPI/Pydantic固定字段、UUID人审，内置页面字段校验 |
| 数据与状态 | 合成字典、InMemorySaver，重启丢失，持久化及租户隔离待接入 |
| Redis | 固定小快照无需缓存，单进程忙时429 |
| 对象存储 | 无导出文件接收，暂不需要 |
| 向量/全文/RAG | 游标和ID精确匹配，暂不需要 |
| 队列 | 当前只审已有证据。真实批量采集需另设计队列/重试/幂等 |
| MCP/业务适配 | 三只读本地工具，暂无远程分页请求 |
| 编排 | LangGraph循环和人审，n8n转发源码。Dify和额外LangChain适配无当前需求 |
| 容器/代理 | 单worker回环8116，生产部署待业务接入 |
| 观测评估 | 返回来源与工具轨迹。11项工具测试、3项脚本图测试源码，未运行 |
| 认证审计 | 环境API密钥，审核者名称由调用者填写。强身份与持久审计待接入 |
| 幂等超时重试 | 新提交使用新线程，轮数及HTTP超时限制失败范围，真实导出重试未实现 |
| 人工审批 | 审查报告，动作结果固定false |
| 备份恢复 | 内存检查点需重提，持久恢复待接入 |

直接依赖版本固定，传递锁与平台安装待环境验收。最多20份证据页、每页100个ID，分析最多10页。重复页面身份拒绝，记录重复则报告。唯一ID相同也可能是正常业务版本，真实接入需确定身份口径。来源总量和快照声明需另核可信度。元数据一致不能证明真实业务数据完整。

实际检查仅AST、JSON、链接、围栏、工具作用域、预算、n8n六节点引用/inactive/UUID/8116/无嵌入凭据及Git选定文件。模型、测试、平台、课堂脚本均未执行，无真实模型轨迹。

2026-11-05阅读GitHub官方分页的next链接与逐页收集说明，作为分页终止的对照。此处游标及快照契约为原创样例。Ollama使用工具结果回传，LangGraph使用interrupt/checkpointer/Command。 [GitHub分页](https://docs.github.com/en/rest/using-the-rest-api/using-pagination-in-the-rest-api) · [Ollama](https://docs.ollama.com/capabilities/tool-calling) · [LangGraph](https://docs.langchain.com/oss/python/langgraph/interrupts)
