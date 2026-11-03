# 制造批次追溯影响审查 Agent

面向制造质量与仓储追溯人员：从一个待调查原料批次出发，沿“投入→产出”关系列出候选下游批次、证据路径与搜索缺口，减少手工多表追查。只使用合成工业批次，不执行召回、隔离、库存修改或客户通知。

输入：case_id、lot_id、带时区as_of、description。输出：候选下游批次、跳数、一条最短关系证据路径、截断边、快照限制、来源及模型工具轨迹，交人工审查。可达关系不是缺陷证明，也不代表真实召回范围已完整确定。

## 流程

n8n提交 → FastAPI鉴权校验 → LangGraph模型选择lookup_lot、lookup_links、assess_impact → 读取结果解释 → 人工approve/reject。

模型四轮、每轮最多三工具；三项成功并引用source后才进入人审。确定性工具使用有向广度优先遍历，当前范围固定最多3跳；每节点只入队一次，输入最多100节点/200边，防止关系循环造成无限处理。只沿下游方向，不把共同原料或其他投入误当成下游。

样例预期：原料A的三跳候选为混料B、包装C、发运D；D到再包装E为已知截断边，不能声称查全。另一原料X投入B，不是A的下游。报告仍需人工核原始生产记录、记录缺失、产品用途、当前状态和正式处置规则。

## 运行

前提Python3.11+，使用者自行准备Ollama服务及支持工具调用的模型；手动执行：

```powershell
cd examples/lot-impact-review
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:LOT_IMPACT_API_KEY = Read-Host '本地API密钥'
$env:OLLAMA_MODEL = 'qwen3:4b'
.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8114 --workers 1
```

另一终端进入同一目录：

```powershell
$headers = @{'X-API-Key' = Read-Host '同一本地API密钥'}
$case = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8114/triage -Headers $headers -ContentType application/json -Body (Get-Content sample.json -Raw -Encoding UTF8)
$case | ConvertTo-Json -Depth 20
$review = @{decision='approve'; reviewer='demo-reviewer'} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8114/threads/$($case.thread_id)/review" -Headers $headers -ContentType application/json -Body $review
```

验收预期：candidate_lots三条、visited_node_count=4、frontier_edges一条、limitations含hop_budget_truncated。recall_authorized=false、actions_executed=false；approve只接受分析建议。

[n8n工作流](n8n-workflow.json)保持inactive。导入后两个Webhook设Header Auth、两个HTTP节点设X-API-Key凭据；先使用test webhook。容器运行需把回环地址改成受控可达API地址；审核入口传返回UUID thread_id、decision、reviewer。没有接入真实MES/WMS系统。

LangGraph负责工具循环与人工暂停，n8n只转发。小关系表无需图数据库、RAG或Dify知识工作流；直接Ollama接口无需额外LangChain适配。单worker回环、内存状态重启丢失，审核者文字不等于身份认证。

手动测试：`.\.venv\Scripts\python.exe -m unittest -v test_tools test_graph`。工程检查与基建取舍见[CHECKS.md](CHECKS.md)，复用入口[SKILL.md](SKILL.md)。原创MIT，第三方依赖保留许可。
