# 库存盘点差异调查 Agent

面向仓库主管：盘点数量与账面不一致时，查账面、盘点及近期流水，让程序计算差额，再由模型整理带来源的复核建议。区别于设备维修，本例处理数量对账和证据不足，不能根据一笔待入账流水自动认定原因。

## 流程

`n8n盘点入口 → FastAPI → LangGraph模型选工具 → 读取库存/流水/计算差额 → 人工中断 → n8n审核入口 → 返回审核记录`。

输入：case_id、sku（商品编号）、description。示例账面100件、盘点94件，计算工具输出 -6件。输出含thread_id、pending_review、建议与来源、工具轨迹。数据全部合成，审核通过也不调整库存。

## 运行入口

Python 3.12+，Ollama/qwen3:4b。进入本目录：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:INVENTORY_API_KEY = '替换为本地随机密钥'
.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8093 --workers 1
```

POST `/triage`，头 `X-API-Key`，请求体见sample.json。保留返回的thread_id。人工复核后POST `/threads/{thread_id}/review`，请求体为 `{"decision":"approve","reviewer":"demo-reviewer"}`，或decision=reject。approve只接受建议，绝不执行库存调整。

导入n8n-workflow.json，保持停用。两个Webhook节点配置Header Auth入口凭据；两个HTTP节点配置Header Auth API凭据（X-API-Key）。提交Webhook路径inventory-case；审核路径inventory-review，审核请求体增加thread_id。API默认127.0.0.1:8093，Docker内需改成实际可达地址。工作流返回API的响应体和状态码，HTTP超时或断网会终止，禁止盲目重复提交。

## 工程取舍

使用：Ollama模型、JSON契约、LangGraph状态与人工暂停恢复、n8n集成、FastAPI密钥、工具白名单、同SKU参数限制、四轮模型上限、120秒请求超时、来源校验。计算用整数件数，仅适用于本例统一单位、同一快照；小数单位应改Decimal并明确换算规则。

暂不使用：Dify应用平台、语义RAG及向量索引（当前是极小结构化数据）；Redis缓存、对象存储、队列（单个只读案例）；生产数据库及持久检查点（演示用内存）；容器反向代理（本地CLI服务配置）。独立工具适配无需另外引入LangChain，LangGraph传递依赖由安装器解析。计划扩展：持久状态、请求幂等、身份权限、异步任务、运行观测与回归评估、备份恢复。密钥及轨迹只留本地，模型不上传。

边界：内存检查点随服务重启消失，必须单进程。共享密钥面向受信任操作员，reviewer为自报姓名。模型文字不证明业务事实，来源校验仅确认引用了已返回来源；主管须核对盘点时间、单位与出入库凭证。服务繁忙返回429，提交没有幂等去重。

源码及文档遵循仓库MIT；Qwen3保留Apache-2.0许可，其他依赖遵循上游许可。[Skill](SKILL.md) · [工程检查记录](CHECKS.md)。

官方资料（核查2026-10-10）：[LangGraph人工中断](https://docs.langchain.com/oss/python/langgraph/interrupts)、[n8n HTTP节点](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/)、[Ollama工具调用](https://docs.ollama.com/capabilities/tool-calling)。
