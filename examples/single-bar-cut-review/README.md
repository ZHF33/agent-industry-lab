# 单根棒料下料复核 Agent

面向工艺员。按最长件优先截取，可能让同一根料交付更少成品长度；忽略锯缝又会出现名义可排、实际超长。输入棒料编号、复核时点和说明，模型自主选择只读工具读取策略、固定棒料/单件需求快照和组合结果，最多四轮后交人工审核。

工具枚举最多10个单件需求的全部子集，先最大化成品总长度，再选切数更少的方案，最后按件号稳定打破并列。每件按一次完整锯缝计消耗。样例1000 mm棒料、锯缝5 mm，需求600/450/450 mm；选两件450，成品900、锯缝10、余料90，600件未选。

工艺员核对材料、实际可用长度、端面修整、夹持余量、尺寸公差和交期，再接受或退回报告。这是单根、同材、单次组合建议；不处理多棒料全局优化，不生成机床指令。每件一次锯缝是合成工艺约定，真实切法须单独确认。

## 运行

准备 Python 3.11+、Ollama 及支持工具调用的模型。在 PowerShell 手动执行。

```powershell
cd examples/single-bar-cut-review
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:CUT_API_KEY = Read-Host '本地 API 密钥'
$env:OLLAMA_MODEL = 'qwen3:4b'
.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8137 --workers 1
```

另一终端在相同目录提交和审核。

```powershell
$headers = @{'X-API-Key' = Read-Host '同一密钥'}
$case = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8137/triage -Headers $headers -ContentType application/json -Body (Get-Content sample.json -Raw -Encoding UTF8)
$case | ConvertTo-Json -Depth 20
$review = @{decision='approve'; reviewer='demo-reviewer'} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8137/threads/$($case.thread_id)/review" -Headers $headers -ContentType application/json -Body $review
```

[n8n 工作流](n8n-workflow.json)提供提交和审核入口。Webhook 设置 Header Auth，HTTP 节点配置 X-API-Key 凭据。使用 Test Webhook。容器环境填写可达的受控 API 地址。内存审核状态随单 worker 进程保留，重启后重新提交。

手动验收命令为 `.\.venv\Scripts\python.exe -m unittest -v test_tools test_graph`。参见[工程记录](CHECKS.md)与[Skill](SKILL.md)。原创 MIT，依赖保留各自许可。
