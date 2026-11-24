# 压缩空气压力告警复核 Agent

面向设备工程师。单阈值判断会让临界压力来回切换告警，采样中断又可能让旧状态被误当成当前状态。输入系统编号、复核时点和说明，模型自主选择工具读取固定压力记录、双阈值策略及复盘结果，最多四轮后形成待审报告。

合成策略：低于600 kPa进入low，达到650 kPa恢复normal；中间带保留先前状态。采样间隔超过30秒先重置unknown，再按当前读数判断；复核时最后读数超过30秒也显示unknown。八条样例状态依次为normal、low、low、low、normal、unknown、low、normal，低压进入2次，low到normal恢复2次，中断重置1次。

设备工程师核对传感器、单位、初始状态、采样连续性及实际维护需求，再接受或退回复盘报告。阈值为教学合成约定，接受报告不代表设备安全放行。报告不控制设备，不修改实时告警。

## 运行

准备 Python 3.11+、Ollama 及支持工具调用的模型。在 PowerShell 手动执行。

```powershell
cd examples/pressure-hysteresis-review
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:PRESSURE_API_KEY = Read-Host '本地 API 密钥'
$env:OLLAMA_MODEL = 'qwen3:4b'
.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8135 --workers 1
```

另一终端在相同目录提交和审核。

```powershell
$headers = @{'X-API-Key' = Read-Host '同一密钥'}
$case = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8135/triage -Headers $headers -ContentType application/json -Body (Get-Content sample.json -Raw -Encoding UTF8)
$case | ConvertTo-Json -Depth 20
$review = @{decision='approve'; reviewer='demo-reviewer'} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8135/threads/$($case.thread_id)/review" -Headers $headers -ContentType application/json -Body $review
```

[n8n 工作流](n8n-workflow.json)提供提交和审核入口。Webhook 设置 Header Auth，HTTP 节点配置 X-API-Key 凭据。使用 Test Webhook。容器环境填写可达的受控 API 地址。内存审核状态随单 worker 进程保留，重启后重新提交。

手动验收命令为 `.\.venv\Scripts\python.exe -m unittest -v test_tools test_graph`。参见[工程记录](CHECKS.md)与[Skill](SKILL.md)。原创 MIT，依赖保留各自许可。
