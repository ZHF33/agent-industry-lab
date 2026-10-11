# 供应商报价复核 Agent

采购主管收到多家报价，单价便宜却可能运费更高、交期更晚、币种不同。本案例查询合成询价与报价，由计算工具生成可比总价，再让模型整理带来源的人工复核建议。

## 输入与输出

输入case_id、rfq_id（询价编号）、description，见sample.json。输出thread_id、pending_review、cost_comparison、建议及来源。合成样例采购100件：A为1040.00 CNY、5天；B为1070.00 CNY、9天；C缺运费，不能当零运费；D使用USD，不直接与CNY排名。总价口径为货价加运费、税前，未包含税费、保险等其他费用。

`n8n询价入口 → FastAPI → LangGraph模型选工具 → 需求/报价/计算工具 → 人工暂停 → n8n审核入口 → 恢复并记录审核`。模型必须经过三个工具才能交审核。人工核对报价原件、费用口径、交期和供应商条件，approve只记录接受建议，不下单、不付款、不联系供应商。

## 运行

Python3.12+，已配置Ollama与qwen3:4b；进入本目录：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:PROCUREMENT_API_KEY = '替换为本地随机密钥'
.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8094 --workers 1
```

POST `/triage`，头X-API-Key，正文为sample.json。保存返回thread_id；人工审核后POST `/threads/{thread_id}/review`，正文 `{"decision":"approve","reviewer":"demo-reviewer"}`，或decision=reject。

导入n8n-workflow.json，默认停用。两个Webhook节点配置Header Auth入口凭据；两个HTTP节点配置Header Auth API凭据，头名X-API-Key、值与环境变量相同。凭据不进入工作流文件。提交Webhook路径supplier-quote-case，审核路径supplier-quote-review；审核正文包含thread_id、decision、reviewer。默认API地址127.0.0.1:8094，Docker环境须改为实际可达地址。工作流转发API状态码与结果；连接中断或超时停止执行，不盲目重试提交。

## 基建选型

使用Ollama推理、严格JSON契约、业务工具适配、LangGraph状态/人工中断、n8n调用、FastAPI密钥与串行锁、四轮上限、请求超时和来源检查。金额为字符串Decimal，输出保留两位小数，ROUND_HALF_UP；币种与单位不匹配、费用缺失会保留问题而非强行计算。

暂不需要Dify或独立LangChain适配（当前模型接口简单）、RAG/向量与全文检索（报价是小型结构化资料）、Redis/对象存储（无大型文档与缓存）、队列及数据库（单任务演示）、容器反向代理（提供本地启动入口）。状态用内存，重启丢失；单worker，繁忙返回429。共享密钥只适合受信任操作员，审核人姓名自报。

后续按业务增加持久状态、幂等请求、队列、身份权限、观测评估、备份恢复。提交没有重复去重，响应不确定时先人工确认；金融金额精度和舍入需按真实合同重新确定。现阶段只有固定合成报价，不抽取PDF，不做汇率换算；来源出现不代表建议业务正确。

[操作Skill](SKILL.md) · [检查记录](CHECKS.md)。源码遵循仓库MIT，上游模型及依赖保留自身许可。

官方资料核查2026-10-11：[Python Decimal](https://docs.python.org/3/library/decimal.html)、[LangGraph中断](https://docs.langchain.com/oss/python/langgraph/interrupts)、[n8n HTTP调用](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/)。
