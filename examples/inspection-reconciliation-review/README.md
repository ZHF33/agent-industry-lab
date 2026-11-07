# 设备点检记录对账 Agent

面向设备维护班组和质量复核人员。它把计划清单与已收记录按设备和点检项匹配，标出缺项、计划外记录、多条结果及冲突。班组根据来源核实实际点检情况，再决定后续处置。

提交 case_id、checklist_id、带时区的 as_of 和 description。模型自主调用 lookup_checklist、lookup_observations、assess_reconciliation，最多四轮，每轮三工具。三项取证和来源引用齐备后交人工复核。合成样例预期 PUMP-A 的 TEMP 缺项、SEAL 结果冲突，PUMP-C 的 TEMP 在计划外。人工批准只接受报告。

## 运行

准备 Python 3.11+、Ollama 及支持工具调用的模型。在 PowerShell 手动执行。

```powershell
cd examples/inspection-reconciliation-review
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:INSPECTION_RECONCILIATION_API_KEY = Read-Host '本地 API 密钥'
$env:OLLAMA_MODEL = 'qwen3:4b'
.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8118 --workers 1
```

另一终端在相同目录提交和审核。

```powershell
$headers = @{'X-API-Key' = Read-Host '同一密钥'}
$case = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8118/triage -Headers $headers -ContentType application/json -Body (Get-Content sample.json -Raw -Encoding UTF8)
$case | ConvertTo-Json -Depth 20
$review = @{decision='approve'; reviewer='demo-reviewer'} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8118/threads/$($case.thread_id)/review" -Headers $headers -ContentType application/json -Body $review
```

[n8n 工作流](n8n-workflow.json)提供提交和审核入口。Webhook 设置 Header Auth，HTTP 节点配置 X-API-Key 凭据。使用 Test Webhook。容器环境填写可达的受控 API 地址。内存审核状态随单 worker 进程保留，重启后重新提交。

手动验收命令为 `.\.venv\Scripts\python.exe -m unittest -v test_tools test_graph`。参见[工程记录](CHECKS.md)与[Skill](SKILL.md)。原创 MIT，依赖保留各自许可。
