# API调用失败分诊 Agent

面向业务集成值班人员：下单POST出现503或超时，先读取操作语义、响应证据和重试策略，工具分类错误与未知结果风险，再交人工调查。超时不证明订单没创建，503不证明根因。

流程：n8n提交 → FastAPI → LangGraph自主调用事件/观测/分类工具 → 人工暂停 → n8n审核 → 恢复记录。输入case_id、incident_id、description，见sample.json；输出thread_id、failure_report、来源与建议。approve只接受调查建议，不重试、不修改权限或凭据、不发消息。观测全部合成，不调用真实业务API。

## 运行

Python3.12+、本地Ollama/qwen3:4b；在本目录：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:FAILURE_API_KEY = '替换为本地随机密钥'
.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8101 --workers 1
```

POST /triage，X-API-Key头，正文sample.json；保存thread_id。人工核对后POST /threads/{thread_id}/review，正文 `{"decision":"approve","reviewer":"demo-reviewer"}` 或reject。

导入n8n-workflow.json，保持停用。Webhook配置独立Header Auth入口凭据；HTTP节点配置Header Auth（X-API-Key与环境变量一致）。提交路径api-failure-case，审核路径api-failure-review；审核体含thread_id、decision、reviewer。默认API127.0.0.1:8101，Docker须改可达地址。状态码/正文转发，断网超时终止，不自动重提。

## 业务边界与基建

工具将401、403、429、服务端错误、超时及连接错误分开；对写请求一律要求先核对业务状态。只有GET/HEAD的瞬态问题标记为“可由人工考虑重试”，不是自动重试许可。idempotency_supported字段只作资料，没有据此放行写重试。没有判断根因或实现熔断、退避执行器。

采用Ollama、严格JSON契约、LangGraph状态和人工中断、n8n、FastAPI密钥与串行锁、工具范围限制、四轮上限、120秒模型请求超时及510秒HTTP等待。内存检查点重启丢失，单worker，繁忙429。共享密钥面向受信任操作员，reviewer自报姓名。

暂不需要Dify/独立LangChain/RAG全文向量检索（小型结构化观测）、Redis/对象存储（无大文件缓存）、队列/数据库/容器反向代理（本地单任务）。未来按业务加入持久状态、身份权限、提交幂等、异步队列、观测评估和备份恢复。当前诊断API本身也没有提交去重，响应不确定需人工确认。[Skill](SKILL.md) · [工程记录](CHECKS.md)。源码MIT，上游依赖和模型保留许可。
