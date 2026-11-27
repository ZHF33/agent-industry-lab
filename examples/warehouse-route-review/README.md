# 仓库通道绕行复核 Agent

面向仓管员。地图上的短路可能已关闭，单向通道也不能自动反向通行。输入地图编号、复核时点和说明，模型自主选择工具读取固定起终点策略、通道快照和最短路结果，最多四轮后交人工审核。

工具排除明确关闭的有向边，按整数米距离计算最短路径，报告节点序列、总距离、关闭边及节点距离确认轨迹。合成地图中ENTRY-A-EXIT共4米，但A到EXIT关闭；可用方案ENTRY-B-EXIT共7米。无可达路径时返回unreachable，距离为空，不用0冒充可达。

仓管员核对地图完整性、现场通道状态、通行权限及设备尺寸后接受或退回报告。最短仅指当前快照中的距离；接受报告不证明现场安全，不控制车辆、机器人或人员，不用于应急疏散。

## 运行

准备 Python 3.11+、Ollama 及支持工具调用的模型。在 PowerShell 手动执行。

```powershell
cd examples/warehouse-route-review
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:ROUTE_API_KEY = Read-Host '本地 API 密钥'
$env:OLLAMA_MODEL = 'qwen3:4b'
.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8138 --workers 1
```

另一终端在相同目录提交和审核。

```powershell
$headers = @{'X-API-Key' = Read-Host '同一密钥'}
$case = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8138/triage -Headers $headers -ContentType application/json -Body (Get-Content sample.json -Raw -Encoding UTF8)
$case | ConvertTo-Json -Depth 20
$review = @{decision='approve'; reviewer='demo-reviewer'} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8138/threads/$($case.thread_id)/review" -Headers $headers -ContentType application/json -Body $review
```

[n8n 工作流](n8n-workflow.json)提供提交和审核入口。Webhook 设置 Header Auth，HTTP 节点配置 X-API-Key 凭据。使用 Test Webhook。容器环境填写可达的受控 API 地址。内存审核状态随单 worker 进程保留，重启后重新提交。

手动验收命令为 `.\.venv\Scripts\python.exe -m unittest -v test_tools test_graph`。参见[工程记录](CHECKS.md)与[Skill](SKILL.md)。原创 MIT，依赖保留各自许可。
