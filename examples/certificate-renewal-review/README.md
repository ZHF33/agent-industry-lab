# 证书续期证据复核 Agent

面向运维与应用负责人：证书资产即将到期，续期单却只写“已签发”。Agent读取合成资产、续期记录与策略，用时间工具计算剩余有效期和资料新鲜度，再给人工复核建议。签发、部署与线上实际生效分别判断。

流程：n8n提交 → FastAPI校验 → LangGraph模型自主选择三个只读工具、读取结果并继续 → 人工中断 → n8n审核入口 → 恢复记录。输出含建议、来源、工具轨迹与expiry_report。approve只记录接受建议；不续签、不改DNS、不部署、不扫描端点。

## 启动

前提：Python3.12+，已有支持工具调用的Ollama及qwen3:4b。模型可用OLLAMA_MODEL指定。以下命令供使用者手动执行，在本目录：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:CERT_API_KEY = '换成自己生成的随机密钥'
.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8103 --workers 1
```

提交合成案例：

```powershell
$headers = @{ 'X-API-Key' = $env:CERT_API_KEY }
$result = Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8103/triage' -Headers $headers -ContentType 'application/json' -Body (Get-Content sample.json -Raw)
$result | ConvertTo-Json -Depth 20
# 人工阅读工具报告与建议后，再选择approve或reject。
$review = @{decision='approve'; reviewer='demo-reviewer'} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8103/threads/$($result.thread_id)/review" -Headers $headers -ContentType 'application/json' -Body $review
```

输入case_id、asset_id、as_of、description；as_of须含UTC偏移，使用固定参考时刻便于重现。合成资产CERT-DEMO-01在样例时刻距离资产快照到期恰好72小时，因此snapshot_urgency为critical，freshness为fresh_snapshot，replacement_deployment为unconfirmed，current_endpoint_status为unknown。当前端点未查询，证书链、域名匹配与吊销检查均不在工具范围。

## n8n和Skill

导入[n8n-workflow.json](n8n-workflow.json)，默认inactive。提交路径certificate-renewal-case，审核路径certificate-renewal-review；审核正文含thread_id、decision、reviewer。Webhook节点设置独立Header Auth凭据；HTTP节点设置X-API-Key Header Auth凭据，对应CERT_API_KEY。JSON不嵌入凭据。容器中的127.0.0.1指容器自身，需要改成可达API地址。HTTP等待510秒，不自动重试提交。上游网络失败时先确认任务状态，再考虑人工重提。

[可复用Skill](SKILL.md) · [检查与基建选择](CHECKS.md) · [可选测试](test_tools.py)。

采用LangGraph管理工具循环与人工恢复，n8n连接两个业务入口；FastAPI提供严格契约。结构化资产无需RAG或向量库；本例不额外引入Dify或独立LangChain编排。状态为单进程内存，服务重启会丢失；只向可信操作员开放，共享密钥不是多租户身份系统。模型建议仍需人工对照报告核实。

源码MIT，依赖与模型许可各自保留。数据全部合成，无真实域名、私钥、证书文件或业务日志。
