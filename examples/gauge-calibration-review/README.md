# 量具校准证据复核 Agent

供计量员和质量工程师复核量具的测点记录。输入 case_id、gauge_id、带偏移的 as_of 和 description。模型最多四轮选择只读工具，读取测点、读数和区间计算结果，再提交含来源和工具轨迹的报告。计量员核对原始记录后接受或退回报告。

案例使用合成微米整数和 ±5 µm 演示容差。样例 P10 区间位于容差内，P20 跨界，P30 在容差外，P40 缺读数。人工审核确认的是证据报告。

## 运行

准备 Python 3.11+、Ollama 及支持工具调用的模型。在 PowerShell 手动执行。

```powershell
cd examples/gauge-calibration-review
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:GAUGE_CALIBRATION_API_KEY = Read-Host '本地 API 密钥'
$env:OLLAMA_MODEL = 'qwen3:4b'
.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8123 --workers 1
```

另一终端在相同目录提交和审核。

```powershell
$headers = @{'X-API-Key' = Read-Host '同一密钥'}
$case = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8123/triage -Headers $headers -ContentType application/json -Body (Get-Content sample.json -Raw -Encoding UTF8)
$case | ConvertTo-Json -Depth 20
$review = @{decision='approve'; reviewer='demo-reviewer'} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8123/threads/$($case.thread_id)/review" -Headers $headers -ContentType application/json -Body $review
```

[n8n 工作流](n8n-workflow.json)提供提交和审核入口。Webhook 设置 Header Auth，HTTP 节点配置 X-API-Key 凭据。使用 Test Webhook。容器环境填写可达的受控 API 地址。内存审核状态随单 worker 进程保留，重启后重新提交。

手动验收命令为 `.\.venv\Scripts\python.exe -m unittest -v test_tools test_graph`。参见[工程记录](CHECKS.md)与[Skill](SKILL.md)。原创 MIT，依赖保留各自许可。
