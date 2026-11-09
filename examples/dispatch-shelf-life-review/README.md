# 到货批次效期复核 Agent

面向出库计划员和质量复核员。按计划到货时间核查每个批次的剩余效期，区分达到演示阈值、差一秒、到货即到期、缺日期和缺批次记录。提交 case_id、shipment_id、带偏移的 as_of 和 description。模型选择只读工具并读取结果，最多四轮，报告附批次和来源，人工复核后接受或退回报告。

样例采用合成的24小时要求。LOT-A 达标，LOT-B 少1秒，LOT-C 到货即到期，LOT-D 缺日期，LOT-E 缺记录。审核对象为报告，实际放行由业务人员另行办理。

## 运行

准备 Python 3.11+、Ollama 及支持工具调用的模型。在 PowerShell 手动执行。

```powershell
cd examples/dispatch-shelf-life-review
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:DISPATCH_SHELF_LIFE_API_KEY = Read-Host '本地 API 密钥'
$env:OLLAMA_MODEL = 'qwen3:4b'
.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8120 --workers 1
```

另一终端在相同目录提交和审核。

```powershell
$headers = @{'X-API-Key' = Read-Host '同一密钥'}
$case = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8120/triage -Headers $headers -ContentType application/json -Body (Get-Content sample.json -Raw -Encoding UTF8)
$case | ConvertTo-Json -Depth 20
$review = @{decision='approve'; reviewer='demo-reviewer'} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8120/threads/$($case.thread_id)/review" -Headers $headers -ContentType application/json -Body $review
```

[n8n 工作流](n8n-workflow.json)提供提交和审核入口。Webhook 设置 Header Auth，HTTP 节点配置 X-API-Key 凭据。使用 Test Webhook。容器环境填写可达的受控 API 地址。内存审核状态随单 worker 进程保留，重启后重新提交。

手动验收命令为 `.\.venv\Scripts\python.exe -m unittest -v test_tools test_graph`。参见[工程记录](CHECKS.md)与[Skill](SKILL.md)。原创 MIT，依赖保留各自许可。
