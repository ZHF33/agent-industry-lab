# 商品缓存一致性调查 Agent

面向电商运营与值班工程师：商品权威资料已经改价，页面缓存仍显示旧价，但TTL还有三分钟。Agent比对合成权威资料和缓存快照的产品身份、版本、币种与价格，区分缓存生命周期和业务新鲜度，给人工调查建议。

流程：n8n入口 → FastAPI严格输入 → LangGraph模型自主选择权威资料/缓存/比较工具、读取反馈 → 人工中断 → 审核恢复。输入case_id、product_id、含时区as_of、description；输出thread_id、consistency_report、来源和工具轨迹。最多四轮，每消息三工具，错误参数可纠正。

合成PRODUCT-DEMO-01：权威v2价格9.00USD，缓存v1价格8.50USD，观测TTL180秒；工具返回版本不匹配、价差-0.50。正TTL不说明业务资料最新，TTL投影不证明现在仍有该键；没有查询真实结算或执行清缓存。

## 手动运行

前提Python3.12+，已有Ollama与支持工具调用的qwen3:4b；可设OLLAMA_MODEL。进入本目录：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:CACHE_API_KEY = '替换为自己生成的随机密钥'
.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8106 --workers 1
```

提交与审核：

```powershell
$headers = @{ 'X-API-Key' = $env:CACHE_API_KEY }
$result = Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8106/triage' -Headers $headers -ContentType 'application/json' -Body (Get-Content sample.json -Raw)
$result | ConvertTo-Json -Depth 20
# 人工对照来源/版本后选择approve或reject。
$review = @{decision='approve'; reviewer='demo-reviewer'} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8106/threads/$($result.thread_id)/review" -Headers $headers -ContentType 'application/json' -Body $review
```

只支持合成ID，approve只记录建议，不删除/刷新键、不改TTL、不改价或收费。工具无Redis/数据库/结算平台连接，不读取真实客户资料。

## 工作流与工程边界

导入[n8n-workflow.json](n8n-workflow.json)，默认停用；提交product-cache-case，审核product-cache-review（正文thread_id、decision、reviewer）。Webhook配置独立Header Auth，HTTP节点配置X-API-Key Header Auth，与CACHE_API_KEY一致。JSON无密钥，等待510秒、不自动重提；容器需将127.0.0.1改成可达API地址。

采用LangGraph管理工具与人工状态，n8n管理入口。合成字典精确查询无需RAG/向量库，不重复引入Dify或独立LangChain。状态只在内存，单worker、串行锁忙时429；共享密钥面向可信操作员，不提供多租户身份系统。

TTL=-2表示观测时未找到，-1表示观测时无过期；非负数按固定参考时刻做投影，不知道期间是否被刷新、删除或淘汰。来源版本仅作相等比较，不假定v字符串可排序。60秒证据年龄是教学策略；旧快照或产品错配时不算价差。真实多层缓存、失效通知、并发回填竞态需独立接入与验证。

[Skill](SKILL.md) · [工程检查](CHECKS.md)。源码MIT；上游依赖与模型保留许可。只发布合成元数据，不含运行库、密钥或日志。
