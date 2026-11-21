# 单品批次先到期拣选复核 Agent

面向仓库拣选计划员。一个需求可能跨多个批次，账面有货还需要核对使用时点和质量放行。输入需求编号、复核时间和说明，模型选择读取需求、批次快照和拣选计划工具，读取结果后形成建议，最多四轮。

规则先排除使用时点已到期或质量冻结批次，再按到期时间与批次号排序，从前向后分配到所需数量。报告列出各批次拣选数量、排除理由和缺口，附工具轨迹。合成需求 9 件，A 可分 3、B 可分 5，缺 1。C 到期过早、D 质量冻结。

计划员检查批次、放行证据和实际可用量，再接受或退回报告。接受的是拣选建议，库存预留和仓库作业由人员处理。样例允许同一物料任意拆批，数量单位为件。

## 运行

准备 Python 3.11+、Ollama 及支持工具调用的模型。在 PowerShell 手动执行。

```powershell
cd examples/fefo-pick-review
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:PICK_API_KEY = Read-Host '本地 API 密钥'
$env:OLLAMA_MODEL = 'qwen3:4b'
.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8132 --workers 1
```

另一终端在相同目录提交和审核。

```powershell
$headers = @{'X-API-Key' = Read-Host '同一密钥'}
$case = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8132/triage -Headers $headers -ContentType application/json -Body (Get-Content sample.json -Raw -Encoding UTF8)
$case | ConvertTo-Json -Depth 20
$review = @{decision='approve'; reviewer='demo-reviewer'} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8132/threads/$($case.thread_id)/review" -Headers $headers -ContentType application/json -Body $review
```

[n8n 工作流](n8n-workflow.json)提供提交和审核入口。Webhook 设置 Header Auth，HTTP 节点配置 X-API-Key 凭据。使用 Test Webhook。容器环境填写可达的受控 API 地址。内存审核状态随单 worker 进程保留，重启后重新提交。

手动验收命令为 `.\.venv\Scripts\python.exe -m unittest -v test_tools test_graph`。参见[工程记录](CHECKS.md)与[Skill](SKILL.md)。原创 MIT，依赖保留各自许可。
