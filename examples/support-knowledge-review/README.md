# 客服知识证据审查 Agent

面向售后主管与客服质检：遇到“破损杯子能否退货”的请求，先查对应产品、地区和生效版本的知识条目，再形成带引用的待审回复建议，避免套用旧政策或错产品资料。

输入：case_id、request_id、带时区as_of、description。输出：候选段落、来源版本、匹配词、缺失业务事实、工具轨迹和人工审核状态。全部为合成英文知识片段，建议可用中文生成。

## 流程

n8n提交 → FastAPI严格校验 → LangGraph让模型选择lookup_request/search_knowledge/assess_retrieval → 先按产品、地区、发布状态和生效区间过滤，再按不同查询词重合数检索 → 模型引用实际候选段落 → 具名人工审核。

每轮最多三个工具、最多四轮；工具错误反馈模型修正，耗尽预算失败。所有工具必须成功，存在候选时最终建议必须引用至少一个候选source；无命中必须引用不足证据报告。模型建议单独标advice_untrusted，引用存在不代表结论正确。

## 运行

前提：Python 3.11+、可用的本地Ollama服务及支持工具调用的模型；安装依赖和启动服务由使用者主动执行。

```powershell
cd examples/support-knowledge-review
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:KNOWLEDGE_API_KEY = Read-Host '本地API密钥'
$env:OLLAMA_MODEL = 'qwen3:4b'
.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8108 --workers 1
```

另一终端发送样例：

```powershell
$headers = @{'X-API-Key' = Read-Host '同一本地API密钥'}
$case = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8108/triage -Headers $headers -ContentType application/json -Body (Get-Content sample.json -Raw)
$case | ConvertTo-Json -Depth 20
$review = @{decision='approve'; reviewer='demo-reviewer'} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8108/threads/$($case.thread_id)/review" -Headers $headers -ContentType application/json -Body $review
```

验收预期：仅命中`KB-DEMO-RETURN-v2`；旧版、错误产品和草稿被过滤。输出候选证据及缺少订单日期、损坏证明等信息，进入人工复核。approve只接受建议，不发送客户回复、不批准退款。

[n8n工作流](n8n-workflow.json)保持inactive；导入后为两个Webhook设置Header Auth，并为两个HTTP节点配置`X-API-Key`凭据。先用test webhook，不自动激活。自建n8n与API同机时可用127.0.0.1；容器内127.0.0.1指容器自身，必须改成能访问API的受控地址。提交返回thread_id，复核入口传同一thread_id、decision、reviewer。工作流不接真实工单系统。

## 范围与技术选择

本例实现最小词法检索增强生成路径：结构化范围过滤、原文段落返回、模型利用工具反馈、来源引用和人工审核。检索分数是“不同查询词重合数”，不是BM25或向量相似度，不宣称语义理解或中文分词。检索问题固定在合成请求中，模型自主选择工具与下一步骤，不能改租户或产品范围。

LangGraph负责状态和审核，n8n仅HTTP入口；固定小语料不需向量数据库，Dify知识运营和LangChain模型适配按接入需求再引入。没有真实客户资料、订单接口、退款工具、消息发送或知识库写入。单worker内存检查点重启丢失，示例范围过滤不替代用户权限与租户隔离。

手动检查命令：`.\.venv\Scripts\python.exe -m unittest -v test_tools test_graph`。实际检查与预期见[CHECKS.md](CHECKS.md)，复用入口[SKILL.md](SKILL.md)。原创源码MIT，第三方依赖保留自身许可。
