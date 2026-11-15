# 产线一次检验合格率复核 Agent

面向质量工程师和车间班组长。各产线检验量不同，直接平均各线百分比会扭曲汇总结果。提交 case_id、window_id、带时区偏移的 as_of 和 description，用于选择已封账的合成检验窗口。一次通过按件计，返工后通过不计入分子。

模型自主选择读取策略、读取各线一次检验计数和计算汇总。系统执行只读工具并把结果回送模型，最多四轮。报告含逐线计数、确切分子与分母、门槛判定、来源编号及工具轨迹。质量工程师核对窗口、产线清单和原检验记录后接受或退回报告。

示例中 A 线 90/90，B 线 5/10，C 线确认零检验，汇总 95/100 恰达 95% 门槛。缺一条产线记录时暂缓汇总。设备、检验系统及批次放行由现场人员管理。

## 运行

准备 Python 3.11+、Ollama 及支持工具调用的模型。在 PowerShell 手动执行。

```powershell
cd examples/first-pass-yield-review
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:FPY_API_KEY = Read-Host '本地 API 密钥'
$env:OLLAMA_MODEL = 'qwen3:4b'
.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8126 --workers 1
```

另一终端在相同目录提交和审核。

```powershell
$headers = @{'X-API-Key' = Read-Host '同一密钥'}
$case = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8126/triage -Headers $headers -ContentType application/json -Body (Get-Content sample.json -Raw -Encoding UTF8)
$case | ConvertTo-Json -Depth 20
$review = @{decision='approve'; reviewer='demo-reviewer'} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8126/threads/$($case.thread_id)/review" -Headers $headers -ContentType application/json -Body $review
```

[n8n 工作流](n8n-workflow.json)提供提交和审核入口。Webhook 设置 Header Auth，HTTP 节点配置 X-API-Key 凭据。使用 Test Webhook。容器环境填写可达的受控 API 地址。内存审核状态随单 worker 进程保留，重启后重新提交。

手动验收命令为 `.\.venv\Scripts\python.exe -m unittest -v test_tools test_graph`。参见[工程记录](CHECKS.md)与[Skill](SKILL.md)。原创 MIT，依赖保留各自许可。
