# 返工优先级复核 Agent

面向生产班组长和质量工程师。输入 case_id、line_id、带偏移的 as_of 和 description。模型在最多四轮内选择读取策略、读取返工单和计算排序的只读工具。报告包含逐单结果、逾期标记、缺证清单及工具轨迹，供班组长接受或退回。

合成规则先看严重度，再看承诺时间，最后按工单编号决胜。样例排序为 RW-002、RW-003、RW-001，其中 RW-001 已逾期。RW-004 缺严重度与承诺时间，单列待补。实际排产由班组长结合产能确认。

## 运行

准备 Python 3.11+、Ollama 及支持工具调用的模型。在 PowerShell 手动执行。

```powershell
cd examples/rework-priority-review
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:REWORK_PRIORITY_API_KEY = Read-Host '本地 API 密钥'
$env:OLLAMA_MODEL = 'qwen3:4b'
.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8122 --workers 1
```

另一终端在相同目录提交和审核。

```powershell
$headers = @{'X-API-Key' = Read-Host '同一密钥'}
$case = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8122/triage -Headers $headers -ContentType application/json -Body (Get-Content sample.json -Raw -Encoding UTF8)
$case | ConvertTo-Json -Depth 20
$review = @{decision='approve'; reviewer='demo-reviewer'} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8122/threads/$($case.thread_id)/review" -Headers $headers -ContentType application/json -Body $review
```

[n8n 工作流](n8n-workflow.json)提供提交和审核入口。Webhook 设置 Header Auth，HTTP 节点配置 X-API-Key 凭据。使用 Test Webhook。容器环境填写可达的受控 API 地址。内存审核状态随单 worker 进程保留，重启后重新提交。

手动验收命令为 `.\.venv\Scripts\python.exe -m unittest -v test_tools test_graph`。参见[工程记录](CHECKS.md)与[Skill](SKILL.md)。原创 MIT，依赖保留各自许可。
