# 生产任务依赖审查 Agent

面向生产计划员和班组协调人员，核对一个计划快照中的前置关系、完成状态和当前阻塞。工具给出结构顺序、一个循环示例、依赖条件满足的待处理任务以及状态矛盾，模型读取结果后形成带来源的人工审查建议。

输入为case_id、plan_id、带时区as_of、description。模型自主选择lookup_plan、lookup_tasks、assess_dependencies。最多四轮，每轮三工具，三项结果齐备且引用source后进入人工审核。

合成样例中TASK-A已完成，TASK-B待处理且前置为A，TASK-C等待B，TASK-D正在执行且前置为A。预期ready_pending_tasks仅含B，C列入等待。结构排序表达先后约束，实际派工还需资源、授权和业务规则。

## 运行

Python3.11+。使用者准备Ollama及支持工具调用的模型，然后手动执行。

```powershell
cd examples/task-dependency-review
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:TASK_DEPENDENCY_API_KEY = Read-Host '本地API密钥'
$env:OLLAMA_MODEL = 'qwen3:4b'
.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8117 --workers 1
```

另一终端进入同一目录提交并审核报告。

```powershell
$headers = @{'X-API-Key' = Read-Host '同一密钥'}
$case = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8117/triage -Headers $headers -ContentType application/json -Body (Get-Content sample.json -Raw -Encoding UTF8)
$case | ConvertTo-Json -Depth 20
$review = @{decision='approve'; reviewer='demo-reviewer'} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8117/threads/$($case.thread_id)/review" -Headers $headers -ContentType application/json -Body $review
```

[n8n工作流](n8n-workflow.json)提供提交和审核入口。Webhook配置Header Auth，HTTP节点配置X-API-Key凭据，先用Test webhook。容器环境填写能到达API的受控地址。人工approve只接受分析建议，业务派工由负责人另行处理。

LangGraph负责模型循环与人审，n8n负责入口转发。合成计划精确查表，无当前知识检索需求。单worker回环、内存检查点，重启后需重新提交。

手动验收 `.\.venv\Scripts\python.exe -m unittest -v test_tools test_graph`。[检查记录](CHECKS.md)列实际验证范围与基建选择，[Skill](SKILL.md)提供复用说明。原创MIT，依赖保留许可。
