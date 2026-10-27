# API配额与突发预算审查 Agent

面向业务集成工程师和API值班人员：在准备批量同步前，核对合成流量快照、限流配置版本和请求批次大小，解释突发预算不足与单批容量上限，给出待人工复核的拆批/调度方向。

输入：case_id、service_id、带时区as_of、description。输出：来源、证据时效与版本、理想令牌投影、单批限制、工具调用轨迹和人工审批记录。样例仅合成配置和计数，不含API密钥或真实请求日志。

## 流程

n8n提交 → FastAPI鉴权和严格校验 → LangGraph模型选择lookup_traffic、lookup_limit、assess_budget → 工具精确计算 → 模型引用来源并解释限制 → 具名人工approve/reject。

每轮最多3工具、最多4轮；越范围参数返回错误供模型修正，预算耗尽失败。三个工具均成功后才形成建议。报告以“期间没有其他请求消费、每请求一个令牌、配置稳定”的理想假设推算，不能代替真实限流器或Retry-After响应。待审建议标advice_untrusted。

## 运行

前提：Python 3.11+、可用的本地Ollama服务及支持工具调用的模型；安装依赖和启动服务由使用者主动执行。

```powershell
cd examples/api-quota-review
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:QUOTA_API_KEY = Read-Host '本地API密钥'
$env:OLLAMA_MODEL = 'qwen3:4b'
.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8109 --workers 1
```

另一终端发送样例：

```powershell
$headers = @{'X-API-Key' = Read-Host '同一本地API密钥'}
$case = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8109/triage -Headers $headers -ContentType application/json -Body (Get-Content sample.json -Raw)
$case | ConvertTo-Json -Depth 20
$review = @{decision='approve'; reviewer='demo-reviewer'} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8109/threads/$($case.thread_id)/review" -Headers $headers -ContentType application/json -Body $review
```

验收预期：初始3个令牌、2.5秒按2个/秒补充后，理想投影8个；一次11请求批次超过容量10，不能靠等待让同一原子批次整体通过。报告交人工复核，不重试、不调配额、不发送任何业务请求。

[n8n工作流](n8n-workflow.json)保持inactive；导入后为两个Webhook设置Header Auth，并为两个HTTP节点配置`X-API-Key`凭据。先用test webhook，不自动激活。自建n8n与API同机时可用127.0.0.1；容器内127.0.0.1指容器自身，必须改成能访问API的受控地址。提交返回thread_id，复核入口传同一thread_id、decision、reviewer。工作流不接真实工单系统。

## 技术选择与边界

LangGraph负责工具反馈和审批；n8n仅HTTP业务入口转发。该场景是结构化计数与配置核查，暂不用Dify知识工作流、RAG或向量库；直接Ollama接口足够，不增加独立LangChain适配。

这不是执行限流的网关。没有Redis共享计数、真实API调用、重试调度器、配额修改或消息发送；approve只表示接受建议。单进程内存检查点重启丢失。生产需要分布式原子扣减、可信时钟、租户身份、幂等重试与持久审计等单独设计。

手动验证命令：`.\.venv\Scripts\python.exe -m unittest -v test_tools test_graph`。检查范围在[CHECKS.md](CHECKS.md)，复用入口[SKILL.md](SKILL.md)。原创源码MIT，依赖保留自身许可。
