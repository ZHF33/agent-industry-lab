# 产线事件序号证据复核 Agent

面向生产数据工程师。采集记录可能乱序、重投、缺号或同号内容冲突。输入事件流编号、复核时点和说明，模型选择只读工具读取独立声明的序号范围、固定事件快照和核查结果，再形成补查建议，最多四轮。

报告列出缺号区间、缺号总数、重复序号及原始行位置、冲突序号和工具轨迹。合成窗口要求100–105，收到六条记录但仅四个不同序号，缺101和104，102重复且内容一致，103的两种状态冲突。缺号以区间表示，处理量由收到的记录数控制。

数据工程师核对设备启动实例、序号生成约定、范围声明和来源记录后接受或退回报告。接受的是复核报告，补采与源系统修改由人员处理。

## 运行

准备 Python 3.11+、Ollama 及支持工具调用的模型。在 PowerShell 手动执行。

```powershell
cd examples/event-sequence-review
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:SEQUENCE_API_KEY = Read-Host '本地 API 密钥'
$env:OLLAMA_MODEL = 'qwen3:4b'
.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8133 --workers 1
```

另一终端在相同目录提交和审核。

```powershell
$headers = @{'X-API-Key' = Read-Host '同一密钥'}
$case = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8133/triage -Headers $headers -ContentType application/json -Body (Get-Content sample.json -Raw -Encoding UTF8)
$case | ConvertTo-Json -Depth 20
$review = @{decision='approve'; reviewer='demo-reviewer'} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8133/threads/$($case.thread_id)/review" -Headers $headers -ContentType application/json -Body $review
```

[n8n 工作流](n8n-workflow.json)提供提交和审核入口。Webhook 设置 Header Auth，HTTP 节点配置 X-API-Key 凭据。使用 Test Webhook。容器环境填写可达的受控 API 地址。内存审核状态随单 worker 进程保留，重启后重新提交。

手动验收命令为 `.\.venv\Scripts\python.exe -m unittest -v test_tools test_graph`。参见[工程记录](CHECKS.md)与[Skill](SKILL.md)。原创 MIT，依赖保留各自许可。
