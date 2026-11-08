# 备件领用数量复核 Agent

面向维修领料员和仓库复核员。输入 case_id、request_id、带时区的 as_of 和 description，模型自主选择读取申请、读取出退库流水及核算工具，读取工具结果后整理差异报告。最多四轮，每轮三次调用，报告附来源和工具轨迹，提交人工审核。

同一张申请单内按备件编号分别计算净领用 = 实领 − 退回，差异 = 净领用 − 申请量。样例 BEARING-A 净领7件、少3件；SEAL-B 净领5件、多1件；FILTER-C 退回1件但没有领出记录，需人工追查。输入限定整数件、最多100行，重复流水编号拒绝处理。报告批准表示接受复核记录。

## 运行

准备 Python 3.11+、Ollama 及支持工具调用的模型。在 PowerShell 手动执行。

```powershell
cd examples/spare-issue-review
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:SPARE_ISSUE_API_KEY = Read-Host '本地 API 密钥'
$env:OLLAMA_MODEL = 'qwen3:4b'
.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8119 --workers 1
```

另一终端在相同目录提交和审核。

```powershell
$headers = @{'X-API-Key' = Read-Host '同一密钥'}
$case = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8119/triage -Headers $headers -ContentType application/json -Body (Get-Content sample.json -Raw -Encoding UTF8)
$case | ConvertTo-Json -Depth 20
$review = @{decision='approve'; reviewer='demo-reviewer'} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8119/threads/$($case.thread_id)/review" -Headers $headers -ContentType application/json -Body $review
```

[n8n 工作流](n8n-workflow.json)提供提交和审核入口。Webhook 设置 Header Auth，HTTP 节点配置 X-API-Key 凭据。使用 Test Webhook。容器环境填写可达的受控 API 地址。内存审核状态随单 worker 进程保留，重启后重新提交。

手动验收命令为 `.\.venv\Scripts\python.exe -m unittest -v test_tools test_graph`。参见[工程记录](CHECKS.md)与[Skill](SKILL.md)。原创 MIT，依赖保留各自许可。
