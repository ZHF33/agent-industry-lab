# 访问申请批准时效审查 Agent

面向数据平台运营和审批流程维护者：发现旧批准记录时，检查它是否仍对应同一申请、修订、动作和资源范围，以及是否过期、撤销或已消费，避免把“批准过”误当成“现在可执行”。

输入：case_id、request_id、带时区as_of、description。输出：逐项阻断理由、有效期、来源、模型工具轨迹和待人工审查建议。数据均为合成元数据，不含真实用户身份、访问令牌或业务记录。

## 流程

n8n提交 → FastAPI鉴权校验 → LangGraph模型选择lookup_request、lookup_approval、assess_approval → 读取结果并解释阻断原因 → 人工approve/reject。

最多4轮、每轮3工具，错误反馈供有限修正，三个工具均成功才形成建议。到期边界用as_of>=expires_at；过期、撤销、消费、范围/修订错配等原因可同时列出。无阻断也只表示快照满足本例条件，不意味着实际执行授权。

## 运行

前提：Python 3.11+、可用的本地Ollama服务及支持工具调用的模型；安装依赖和启动服务由使用者主动执行。

```powershell
cd examples/approval-expiry-review
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:APPROVAL_API_KEY = Read-Host '本地API密钥'
$env:OLLAMA_MODEL = 'qwen3:4b'
.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8111 --workers 1
```

另一终端发送样例：

```powershell
$headers = @{'X-API-Key' = Read-Host '同一本地API密钥'}
$case = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8111/triage -Headers $headers -ContentType application/json -Body (Get-Content sample.json -Raw)
$case | ConvertTo-Json -Depth 20
$review = @{decision='approve'; reviewer='demo-reviewer'} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8111/threads/$($case.thread_id)/review" -Headers $headers -ContentType application/json -Body $review
```

验收预期：审核时刻恰等于expires_at，输出approval_expired，要求重新获取授权审核。approve仅接受分诊建议，不续期旧批准、不恢复外部流程、不授予数据访问。

[n8n工作流](n8n-workflow.json)保持inactive；导入后为两个Webhook设置Header Auth，并为两个HTTP节点配置`X-API-Key`凭据。先用test webhook，不自动激活。自建n8n与API同机时可用127.0.0.1；容器内127.0.0.1指容器自身，必须改成能访问API的受控地址。提交返回thread_id，复核入口传同一thread_id、decision、reviewer。工作流不接真实工单系统。

## 技术选择与边界

LangGraph负责本次分诊状态和人工暂停，n8n只转发HTTP；无需RAG、向量库或Dify知识工作流；直接Ollama接口无需独立LangChain适配。具名reviewer字段不是生产身份认证，内置审核者名单仅合成约定。

本例不实现真实批准令牌、单次消费、身份系统、原子执行门或访问权限变更。实际执行端必须重新核对授权、时效和状态并原子消费，不能只依赖此报告。内存检查点重启丢失，仅单worker回环地址。

手动验证：`.\.venv\Scripts\python.exe -m unittest -v test_tools test_graph`。检查范围及基建取舍见[CHECKS.md](CHECKS.md)，复用入口[SKILL.md](SKILL.md)。原创源码MIT，依赖保留自身许可。
