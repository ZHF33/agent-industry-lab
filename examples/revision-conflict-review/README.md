# 工单修订冲突审查 Agent

面向工单运营主管与业务集成人员：审核优先级修改提案时，识别提案基准版本与当前记录快照冲突，避免旧提案被误当成当前操作依据。

输入：case_id、change_id、带时区as_of、description。输出：提案/当前版本、对象与时效核查、字段差异、确定性判定、工具轨迹和待人工审查建议。仅合成工单，不含客户姓名、地址或真实运行日志。

## 流程

n8n提交 → FastAPI鉴权校验 → LangGraph驱动模型选择lookup_change、lookup_record、assess_revision → 比较对象、时间、基准版本与工单状态 → 引用来源解释冲突 → 人工approve/reject。

最多4轮、每轮3个工具；参数越界反馈错误供修正，全部必要工具成功才给建议。缺少基准版本、陈旧证据、对象错配分别处理，不把时间接近当成版本一致。模型文本保留advice_untrusted，确定性报告独立返回。

## 运行

前提：Python 3.11+、可用的本地Ollama服务及支持工具调用的模型；安装依赖和启动服务由使用者主动执行。

```powershell
cd examples/revision-conflict-review
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:REVISION_API_KEY = Read-Host '本地API密钥'
$env:OLLAMA_MODEL = 'qwen3:4b'
.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8110 --workers 1
```

另一终端发送样例：

```powershell
$headers = @{'X-API-Key' = Read-Host '同一本地API密钥'}
$case = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8110/triage -Headers $headers -ContentType application/json -Body (Get-Content sample.json -Raw)
$case | ConvertTo-Json -Depth 20
$review = @{decision='approve'; reviewer='demo-reviewer'} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8110/threads/$($case.thread_id)/review" -Headers $headers -ContentType application/json -Body $review
```

验收预期：提案基于revision=4，工单快照revision=5，输出revision_conflict并要求重新读取/重新审核，不自动合并。即使版本相同也只表示快照匹配；approve只接受审查建议，不修改工单或派单。

[n8n工作流](n8n-workflow.json)保持inactive；导入后为两个Webhook设置Header Auth，并为两个HTTP节点配置`X-API-Key`凭据。先用test webhook，不自动激活。自建n8n与API同机时可用127.0.0.1；容器内127.0.0.1指容器自身，必须改成能访问API的受控地址。提交返回thread_id，复核入口传同一thread_id、decision、reviewer。工作流不接真实工单系统。

## 技术选择

LangGraph管理状态与审批，n8n仅HTTP入口；结构化版本核对无需RAG、向量库或Dify知识工作流，直接Ollama接口无需额外LangChain适配。

这是只读审查，未实现工单写接口、数据库CAS或HTTP If-Match。快照匹配不保证稍后的真实写入成功；生产执行端需原子版本条件和重新授权。内存检查点重启丢失、仅单worker，不能直接当生产协作编辑服务。

手动验证命令：`.\.venv\Scripts\python.exe -m unittest -v test_tools test_graph`。实际检查及基础设施选择见[CHECKS.md](CHECKS.md)，复用入口[SKILL.md](SKILL.md)。原创源码MIT，依赖保留自身许可。
