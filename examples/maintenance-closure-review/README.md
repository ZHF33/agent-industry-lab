# 维修工单结案证据复核 Agent

面向维修文员和维修主管。结案资料里同时可能存在已知失败和缺记录，单一“有附件”标记容易漏掉问题。输入工单编号、复核时间和说明，模型选择只读工具核对必需项与证据结果，读取结果后提出补证说明，最多四轮。

报告列出所有失败项、缺证项、证据编号和工具轨迹。合成工单中维修记录通过、试运行记录失败、余料退回缺证，因此结案准备度为 blocked。试运行补为通过后，仍需余料退回记录。主管核对原始资料后，可接受或退回报告，业务系统结案由人员处理。

## 运行

准备 Python 3.11+、Ollama 及支持工具调用的模型。在 PowerShell 手动执行。

```powershell
cd examples/maintenance-closure-review
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:CLOSURE_API_KEY = Read-Host '本地 API 密钥'
$env:OLLAMA_MODEL = 'qwen3:4b'
.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8131 --workers 1
```

另一终端在相同目录提交和审核。

```powershell
$headers = @{'X-API-Key' = Read-Host '同一密钥'}
$case = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8131/triage -Headers $headers -ContentType application/json -Body (Get-Content sample.json -Raw -Encoding UTF8)
$case | ConvertTo-Json -Depth 20
$review = @{decision='approve'; reviewer='demo-reviewer'} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8131/threads/$($case.thread_id)/review" -Headers $headers -ContentType application/json -Body $review
```

[n8n 工作流](n8n-workflow.json)提供提交和审核入口。Webhook 设置 Header Auth，HTTP 节点配置 X-API-Key 凭据。使用 Test Webhook。容器环境填写可达的受控 API 地址。内存审核状态随单 worker 进程保留，重启后重新提交。

手动验收命令为 `.\.venv\Scripts\python.exe -m unittest -v test_tools test_graph`。参见[工程记录](CHECKS.md)与[Skill](SKILL.md)。原创 MIT，依赖保留各自许可。
