# 出货托盘需求复核 Agent

面向出货计划员。按客户、运输条件或批次划分的装托组可能必须分开装载。输入出货单编号、复核时间和说明，模型选择只读工具核对需求和每托容量，读取结果后交给人工。报告保留每组满托数、尾箱数、需用托盘数及工具轨迹。模型最多四轮。

合成单中 A 组 9 箱、B 组 7 箱，每托均可装 8 箱，因此需 2 托和 1 托。C 组 4 箱缺容量。报告给出已知小计 3 托，总量待补证。审核人员核对装托组、容量来源和现场装载条件后接受或退回报告。接受报告用于备货计划，实际装车由现场处理。

## 运行

准备 Python 3.11+、Ollama 及支持工具调用的模型。在 PowerShell 手动执行。

```powershell
cd examples/pallet-capacity-review
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:PALLET_API_KEY = Read-Host '本地 API 密钥'
$env:OLLAMA_MODEL = 'qwen3:4b'
.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8127 --workers 1
```

另一终端在相同目录提交和审核。

```powershell
$headers = @{'X-API-Key' = Read-Host '同一密钥'}
$case = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8127/triage -Headers $headers -ContentType application/json -Body (Get-Content sample.json -Raw -Encoding UTF8)
$case | ConvertTo-Json -Depth 20
$review = @{decision='approve'; reviewer='demo-reviewer'} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8127/threads/$($case.thread_id)/review" -Headers $headers -ContentType application/json -Body $review
```

[n8n 工作流](n8n-workflow.json)提供提交和审核入口。Webhook 设置 Header Auth，HTTP 节点配置 X-API-Key 凭据。使用 Test Webhook。容器环境填写可达的受控 API 地址。内存审核状态随单 worker 进程保留，重启后重新提交。

手动验收命令为 `.\.venv\Scripts\python.exe -m unittest -v test_tools test_graph`。参见[工程记录](CHECKS.md)与[Skill](SKILL.md)。原创 MIT，依赖保留各自许可。
