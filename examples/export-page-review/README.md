# 分页订单导出完整性审查 Agent

制造运营与数据接入人员可以核查一个订单导出快照的分页证据。Agent读取导出定义和已收集页面，跟随游标关系，给出重复ID、缺页、快照变化、结束标记及数量差异，再交人工审核。

输入为 case_id、export_id、带偏移的 as_of、description。模型自主选择 lookup_export、lookup_pages、assess_export 三个只读工具。最多四轮，每轮三工具。报告包含来源、游标轨迹、差异和人工建议。

样例收集了四条记录，唯一ID为三条，ROW-2重复，游标P2对应页面缺失，目标唯一数量为四。班组需核原导出任务和数据口径，再决定补采流程。审核只确认报告。

## 运行

Python 3.11+，自行准备Ollama服务及支持工具调用的模型。手动启动如下。

```powershell
cd examples/export-page-review
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:EXPORT_PAGE_API_KEY = Read-Host '本地API密钥'
$env:OLLAMA_MODEL = 'qwen3:4b'
.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8116 --workers 1
```

另一终端进入同一目录提交，再用返回的thread_id审核。

```powershell
$headers = @{'X-API-Key' = Read-Host '同一密钥'}
$case = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8116/triage -Headers $headers -ContentType application/json -Body (Get-Content sample.json -Raw -Encoding UTF8)
$case | ConvertTo-Json -Depth 20
$review = @{decision='approve'; reviewer='demo-reviewer'} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8116/threads/$($case.thread_id)/review" -Headers $headers -ContentType application/json -Body $review
```

[n8n工作流](n8n-workflow.json)提供提交/审核两个入口。Webhook设置Header Auth，HTTP节点配置X-API-Key凭据。使用Test webhook，按实际受控网络填写API地址。单worker回环，内存检查点重启后需重新提交。

LangGraph管模型循环与人审，n8n转发业务请求。此固定小清单适合精确查表。Dify知识运营、RAG和额外LangChain适配可在真实检索需求出现后评估。

验收预期为unique_count=3、row_count=4、blocked_cursor=P2、duplicate_ids=[ROW-2]、terminal_seen=false。手动测试命令为 `.\.venv\Scripts\python.exe -m unittest -v test_tools test_graph`。参见[检查记录](CHECKS.md)与[Skill](SKILL.md)。原创MIT，依赖保留许可。
