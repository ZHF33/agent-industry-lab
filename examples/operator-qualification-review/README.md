# 工位人员资格匹配 Agent

面向班组长。只数“人数够不够”会遗漏资格冲突；按第一位合格人员依次填岗，也可能占用后续岗位唯一人选。输入计划编号、复核时点和说明，模型自主选择工具读取岗位要求、人员资格/可用性快照及匹配结果，最多四轮后形成待审方案。

工具建立岗位与可用合格人员的候选关系，采用增广路径调整已有配对，求一人一岗条件下的最大覆盖数，报告候选、配对变化和未匹配岗位。样例先将J-01配给OP-A，处理J-02时把J-01移给OP-B、J-02交给OP-A；J-03因唯一有资格者不可用而缺岗。

班组长核对资格来源、证书有效性、现场可用性和岗位实际条件，再接受或退回方案。接受的是报告；实际派岗由人员另行执行。本例不优化公平、成本或班次时序，不签发真实上岗许可。

## 运行

准备 Python 3.11+、Ollama 及支持工具调用的模型。在 PowerShell 手动执行。

```powershell
cd examples/operator-qualification-review
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:QUALIFICATION_API_KEY = Read-Host '本地 API 密钥'
$env:OLLAMA_MODEL = 'qwen3:4b'
.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8136 --workers 1
```

另一终端在相同目录提交和审核。

```powershell
$headers = @{'X-API-Key' = Read-Host '同一密钥'}
$case = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8136/triage -Headers $headers -ContentType application/json -Body (Get-Content sample.json -Raw -Encoding UTF8)
$case | ConvertTo-Json -Depth 20
$review = @{decision='approve'; reviewer='demo-reviewer'} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8136/threads/$($case.thread_id)/review" -Headers $headers -ContentType application/json -Body $review
```

[n8n 工作流](n8n-workflow.json)提供提交和审核入口。Webhook 设置 Header Auth，HTTP 节点配置 X-API-Key 凭据。使用 Test Webhook。容器环境填写可达的受控 API 地址。内存审核状态随单 worker 进程保留，重启后重新提交。

手动验收命令为 `.\.venv\Scripts\python.exe -m unittest -v test_tools test_graph`。参见[工程记录](CHECKS.md)与[Skill](SKILL.md)。原创 MIT，依赖保留各自许可。
