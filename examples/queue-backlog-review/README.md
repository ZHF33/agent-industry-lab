# 队列积压调查 Agent

面向电商标签任务、异步工单等业务的运维人员：队列积压上升时，读取合成队列快照、区间发布/确认计数与工作进程记录，判断统计是否自洽、资料是否新鲜，并提出人工调查顺序。

流程：n8n提交 → FastAPI严格输入 → LangGraph模型自行选择队列/工作进程/评估工具并读取结果 → 人工中断 → n8n复核 → 恢复记录。输入case_id、queue_id、含偏移as_of和description；输出thread_id、backlog_report、来源、建议与工具轨迹。四轮上限，单消息最多三工具；错误参数可在预算内纠正。

示例5分钟内ready+unacked从120增至300，发布600、确认420，计数平衡；每秒发布2、确认1.4。若假设停止新增且确认吞吐保持不变，300条约214.29秒处理完。这只是情景计算，不是实际清空时间预测。当前输入持续大于确认，不能承诺很快排空；根因也不能仅凭一条工作进程错误就确定。

## 手动运行

前提：Python3.12+，已有Ollama及支持工具调用的qwen3:4b，可用OLLAMA_MODEL指定。进入本目录：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:QUEUE_API_KEY = '替换为自己生成的随机密钥'
.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8105 --workers 1
```

提交和审核：

```powershell
$headers = @{ 'X-API-Key' = $env:QUEUE_API_KEY }
$result = Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8105/triage' -Headers $headers -ContentType 'application/json' -Body (Get-Content sample.json -Raw)
$result | ConvertTo-Json -Depth 20
# 人工核对证据后，选择approve或reject。
$review = @{decision='approve'; reviewer='demo-reviewer'} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8105/threads/$($result.thread_id)/review" -Headers $headers -ContentType 'application/json' -Body $review
```

只支持合成QUEUE-DEMO-01，不连接RabbitMQ或其他真实代理。approve仅记录建议，不重投、确认、清空队列，不扩容、调整prefetch或发送消息。

## 工作流与范围

导入[n8n-workflow.json](n8n-workflow.json)，默认停用。提交路径queue-backlog-case；审核路径queue-backlog-review，正文含thread_id、decision、reviewer。Webhook设置独立Header Auth，HTTP节点Header Auth设置X-API-Key，与QUEUE_API_KEY一致；JSON无凭据。HTTP等待510秒，无自动重试；Docker中的127.0.0.1需改为可达地址。

LangGraph拥有Agent循环，n8n负责入口转发。队列数字是合成遥测，不实现消息代理或消费者；结构化查询无需RAG/向量库，也不重复加入Dify或独立LangChain。单进程内存状态，重启丢失，忙时429；共享密钥面向可信操作员，不是多租户授权。工具报告与模型文字分别审核。

本例假设计数来自同一队列代际、同一窗口，无重试或计数器重置；过期、清空、出站死信单独计入移出项。真实平台的重投、拒绝、TTL、代际变更和采集非原子性需要另设契约，不能直接套公式。确认数不证明真实业务副作用恰好执行一次。

[Skill](SKILL.md) · [工程记录与基建评估](CHECKS.md)。源码MIT，上游依赖与模型保留许可。无数据库、密钥、真实任务正文或运行日志。
