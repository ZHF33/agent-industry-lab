# 装卸月台预约容量复核 Agent

面向仓库调度员。逐张预约看起来都可安排，放在一起可能同时争用月台。输入月台池、复核时间和说明。模型选择只读工具读取月台数、预约时段及复核结果，最多四轮。报告给出峰值、超额窗口、差额及预约编号，附工具轨迹。

合成案例有两个可互换月台。UTC 09:30–10:00 同时需要三个，缺一个。10:00 结束的预约释放月台，同一时刻可交接。调度员检查车辆、月台兼容性和现场缓冲后，可接受或退回报告。现场预约调整由调度员处理。

## 运行

准备 Python 3.11+、Ollama 及支持工具调用的模型。在 PowerShell 手动执行。

```powershell
cd examples/dock-capacity-review
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:DOCK_API_KEY = Read-Host '本地 API 密钥'
$env:OLLAMA_MODEL = 'qwen3:4b'
.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8128 --workers 1
```

另一终端在相同目录提交和审核。

```powershell
$headers = @{'X-API-Key' = Read-Host '同一密钥'}
$case = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8128/triage -Headers $headers -ContentType application/json -Body (Get-Content sample.json -Raw -Encoding UTF8)
$case | ConvertTo-Json -Depth 20
$review = @{decision='approve'; reviewer='demo-reviewer'} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8128/threads/$($case.thread_id)/review" -Headers $headers -ContentType application/json -Body $review
```

[n8n 工作流](n8n-workflow.json)提供提交和审核入口。Webhook 设置 Header Auth，HTTP 节点配置 X-API-Key 凭据。使用 Test Webhook。容器环境填写可达的受控 API 地址。内存审核状态随单 worker 进程保留，重启后重新提交。

手动验收命令为 `.\.venv\Scripts\python.exe -m unittest -v test_tools test_graph`。参见[工程记录](CHECKS.md)与[Skill](SKILL.md)。原创 MIT，依赖保留各自许可。
