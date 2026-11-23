# 来料抽检清单 Agent

面向来料质量员。人工从台账前几行拿样容易遗漏分层、重复拿样，重排文件后也难以复核。输入批次编号、复核时点和说明，模型自主选择工具读取固定总体快照、独立配额和选样结果，最多四轮，形成待人工审核的取样清单。

工具按料件唯一编号与分层计算固定 SHA-256 分数，每层取分数最小的若干件，保留分数及配额缺口。同一快照、种子与算法下，输入行重排不改变结果。合成样例中 A 层三件取两件；B 层仅一件而要求两件，清单共三件，B 层缺一件。

质量员核对总体完整性、料件实物定位、事先批准的种子及配额，再接受或退回清单。接受清单后由人员安排取样。此工具不判定检验合格，不计算 AQL 或缺陷率；固定种子选样只提供可复核清单，不保证统计代表性。

## 运行

准备 Python 3.11+、Ollama 及支持工具调用的模型。在 PowerShell 手动执行。

```powershell
cd examples/inspection-sample-review
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:SAMPLING_API_KEY = Read-Host '本地 API 密钥'
$env:OLLAMA_MODEL = 'qwen3:4b'
.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8134 --workers 1
```

另一终端在相同目录提交和审核。

```powershell
$headers = @{'X-API-Key' = Read-Host '同一密钥'}
$case = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8134/triage -Headers $headers -ContentType application/json -Body (Get-Content sample.json -Raw -Encoding UTF8)
$case | ConvertTo-Json -Depth 20
$review = @{decision='approve'; reviewer='demo-reviewer'} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8134/threads/$($case.thread_id)/review" -Headers $headers -ContentType application/json -Body $review
```

[n8n 工作流](n8n-workflow.json)提供提交和审核入口。Webhook 设置 Header Auth，HTTP 节点配置 X-API-Key 凭据。使用 Test Webhook。容器环境填写可达的受控 API 地址。内存审核状态随单 worker 进程保留，重启后重新提交。

手动验收命令为 `.\.venv\Scripts\python.exe -m unittest -v test_tools test_graph`。参见[工程记录](CHECKS.md)与[Skill](SKILL.md)。原创 MIT，依赖保留各自许可。
