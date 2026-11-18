# 分档电量费用复核 Agent

面向工厂能源管理员。各档电量和单价分开记录，缺档或单位看错会影响估算。提交电表编号、复核时间和说明，模型选择只读工具检查固定快照、费率表和计算结果。报告逐档列出电量、单价、未舍入费用、证据编号和工具轨迹。模型最多四轮。

样例中峰谷各 1,250 Wh，对应 21 和 11 分每千瓦时，合计电量费用 40 分。缺档时报告保留已知金额，总额待补。人工复核用量来源、档位、费率和舍入约定，再接受或退回报告。计算范围为合成电量费用。

## 运行

准备 Python 3.11+、Ollama 及支持工具调用的模型。在 PowerShell 手动执行。

```powershell
cd examples/energy-charge-review
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:ENERGY_API_KEY = Read-Host '本地 API 密钥'
$env:OLLAMA_MODEL = 'qwen3:4b'
.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8129 --workers 1
```

另一终端在相同目录提交和审核。

```powershell
$headers = @{'X-API-Key' = Read-Host '同一密钥'}
$case = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8129/triage -Headers $headers -ContentType application/json -Body (Get-Content sample.json -Raw -Encoding UTF8)
$case | ConvertTo-Json -Depth 20
$review = @{decision='approve'; reviewer='demo-reviewer'} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8129/threads/$($case.thread_id)/review" -Headers $headers -ContentType application/json -Body $review
```

[n8n 工作流](n8n-workflow.json)提供提交和审核入口。Webhook 设置 Header Auth，HTTP 节点配置 X-API-Key 凭据。使用 Test Webhook。容器环境填写可达的受控 API 地址。内存审核状态随单 worker 进程保留，重启后重新提交。

手动验收命令为 `.\.venv\Scripts\python.exe -m unittest -v test_tools test_graph`。参见[工程记录](CHECKS.md)与[Skill](SKILL.md)。原创 MIT，依赖保留各自许可。
