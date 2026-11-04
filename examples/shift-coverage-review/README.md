# 工厂交班证据覆盖审查 Agent

班组长可用它核对一个已结束班次的交接记录。工具将带时区的时间转成 UTC，裁剪到班次窗口，合并重叠记录，再列出证据覆盖、缺口和来源。缺口表示当前快照缺少证据，实际交班情况由班组长复核。

提交 `case_id`、`shift_id`、带时区的 `as_of` 和 `description`。模型自主选择 `lookup_shift`、`lookup_coverage`、`assess_coverage`，最多四轮，每轮三次。报告含时间段、来源、工具轨迹和待审核建议。人工批准只确认报告。样例预期覆盖 220 分钟，10:00–10:20 UTC 缺少 20 分钟证据。

Python 3.11+。请先自行准备 Ollama 和支持工具调用的模型，再手动启动。

```powershell
cd examples/shift-coverage-review
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:SHIFT_COVERAGE_API_KEY = Read-Host '本地 API 密钥'
$env:OLLAMA_MODEL = 'qwen3:4b'
.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8115 --workers 1
```

另一终端在相同目录提交并审核。

```powershell
$headers = @{'X-API-Key' = Read-Host '同一密钥'}
$case = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8115/triage -Headers $headers -ContentType application/json -Body (Get-Content sample.json -Raw -Encoding UTF8)
$case | ConvertTo-Json -Depth 20
$review = @{decision='approve'; reviewer='demo-reviewer'} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8115/threads/$($case.thread_id)/review" -Headers $headers -ContentType application/json -Body $review
```

[n8n 导入文件](n8n-workflow.json)提供两个入口。分别为 Webhook 设置 Header Auth，为 HTTP Request 节点设置 `X-API-Key` 凭据。使用 Test Webhook。容器内的回环地址指向容器自身，请填写可达的 API 地址。重启进程后需重提，因为审核状态保存在内存。

手动验收命令为 `.\.venv\Scripts\python.exe -m unittest -v test_tools test_graph`。参见 [Skill](SKILL.md) 和 [工程检查](CHECKS.md)。
