# 对象版本与保留证据审查 Agent

面向客服升级处理、存储运维：普通读取显示文件不存在时，梳理当前删除标记、历史数据版本及保留证据，输出带来源的人工复核建议。

输入：`case_id`、`object_id`、带时区`as_of`、问题描述。输出：来源、逐版本限制记录、证据时效、模型工具轨迹及待审查建议。样例只含合成元数据，不含文件内容。

## 流程

n8n接收工单 → FastAPI校验及鉴权 → LangGraph驱动模型选择三个只读工具 → 读取版本清单和保留元数据 → 确定性工具核对 → 模型引用来源 → 人工approve/reject。

三工具为`lookup_object_versions`、`lookup_retention`、`assess_retention`。模型最多四轮、每轮三工具；参数越界返回工具错误供修正，轮数耗尽结束失败。当前删除标记与旧数据版本分开；过期或不完整清单降低结论强度。无有效限制记录也不代表允许删除。

## 运行

前提：Python 3.11+、可用的本地Ollama服务及支持工具调用的模型；安装依赖和启动服务由使用者主动执行。

```powershell
cd examples/object-retention-review
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:OBJECT_API_KEY = Read-Host '本地API密钥'
$env:OLLAMA_MODEL = 'qwen3:4b'
.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8107 --workers 1
```

另一终端发送样例：

```powershell
$headers = @{'X-API-Key' = Read-Host '同一本地API密钥'}
$case = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8107/triage -Headers $headers -ContentType application/json -Body (Get-Content sample.json -Raw)
$case | ConvertTo-Json -Depth 20
$review = @{decision='approve'; reviewer='demo-reviewer'} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8107/threads/$($case.thread_id)/review" -Headers $headers -ContentType application/json -Body $review
```

验收预期：样例当前版本为`delete_marker`，旧版`data-v1`记录有保留限制；进入人工审核。审核仅记录建议是否接受，不执行删除、恢复、下载、策略更改或业务通知。模型措辞不作为权限决定。

[n8n工作流](n8n-workflow.json)保持inactive；导入后为两个Webhook设置Header Auth，并为两个HTTP节点配置`X-API-Key`凭据。先用test webhook，不自动激活。自建n8n与API同机时可用127.0.0.1；容器内127.0.0.1指容器自身，必须改成能访问API的受控地址。提交返回thread_id，复核入口传同一thread_id、decision、reviewer。工作流不接真实工单系统。

## 范围与技术选择

LangGraph负责工具循环和人工暂停；n8n负责HTTP入口转发。固定结构元数据无需RAG或向量库；无可视化知识运营需求，暂不用Dify；直接调用Ollama，无需额外LangChain模型适配。API为单进程内存状态，重启丢失，不支持多租户和持久审计，不适合直接暴露公网。

手工验证命令：`.\.venv\Scripts\python.exe -m unittest -v test_tools test_graph`。检查范围与预期分开记录在[工程检查](CHECKS.md)。复用入口：[SKILL.md](SKILL.md)。原创源码遵循仓库MIT许可，依赖保留其各自许可。
