# 装配工单齐套复核 Agent

面向生产计划员和备料员。工单有多种必需物料，即使总库存很多，也可能凑不出完整的一套。输入工单编号、复核时间和说明。模型自主选择读取 BOM（每件产品的物料用量清单）、专属可用量和齐套计算工具，读取结果后给出解释，最多四轮。

报告列出物料用量、目标需求、缺口、可完成整件数、限制物料和证据编号，附工具轨迹。合成工单计划 10 件，每件需壳体 1、螺栓 2、密封圈 1。当前有 10、19、0，齐套为 0 件。密封圈补到 10 后，螺栓限制为 9 件。缺记录时总数待核。

备料员核对 BOM 版本、计量单位和专属可用量，接受或退回报告。实际预留、发料与生产放行由业务人员处理。

## 运行

准备 Python 3.11+、Ollama 及支持工具调用的模型。在 PowerShell 手动执行。

```powershell
cd examples/material-kitting-review
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:KIT_API_KEY = Read-Host '本地 API 密钥'
$env:OLLAMA_MODEL = 'qwen3:4b'
.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8130 --workers 1
```

另一终端在相同目录提交和审核。

```powershell
$headers = @{'X-API-Key' = Read-Host '同一密钥'}
$case = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8130/triage -Headers $headers -ContentType application/json -Body (Get-Content sample.json -Raw -Encoding UTF8)
$case | ConvertTo-Json -Depth 20
$review = @{decision='approve'; reviewer='demo-reviewer'} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8130/threads/$($case.thread_id)/review" -Headers $headers -ContentType application/json -Body $review
```

[n8n 工作流](n8n-workflow.json)提供提交和审核入口。Webhook 设置 Header Auth，HTTP 节点配置 X-API-Key 凭据。使用 Test Webhook。容器环境填写可达的受控 API 地址。内存审核状态随单 worker 进程保留，重启后重新提交。

手动验收命令为 `.\.venv\Scripts\python.exe -m unittest -v test_tools test_graph`。参见[工程记录](CHECKS.md)与[Skill](SKILL.md)。原创 MIT，依赖保留各自许可。
