# 售后退货证据复核 Agent

面向售后主管：查订单、退货资料与内部检查清单，计算申请间隔、核对数量和缺失证据，再交人工审核。合成样例收到2件、申请退1件，送达后13天申请，缺照片。缺证据不等于欺诈，演示政策不代表消费者权利或退款资格。

流程：n8n提交 → FastAPI → LangGraph模型选择订单/证据/评估工具 → 人工暂停 → n8n审核 → 恢复并记录。输入case_id、return_id、description，见sample.json；输出thread_id、return_assessment、来源和建议。approve只接受建议，不退款、不修改订单、不通知客户。

## 运行入口

Python3.12+，本地Ollama/qwen3:4b；进入本目录：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:RETURN_API_KEY = '替换为本地随机密钥'
.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8097 --workers 1
```

POST /triage，X-API-Key头，正文sample.json；保存thread_id。人工复核后POST /threads/{thread_id}/review，正文 `{"decision":"approve","reviewer":"demo-reviewer"}`，或reject。

导入n8n-workflow.json，保持停用。Webhook配置Header Auth独立入口凭据，HTTP节点配置Header Auth，头X-API-Key，与环境变量一致。提交路径return-evidence-case，审核路径return-evidence-review；审核正文包含thread_id、decision、reviewer。API默认127.0.0.1:8097，Docker内须改可达地址。API状态码与结果转发；断网、超时终止，不自动重提。

## 工程选择

采用Ollama、JSON契约、LangGraph状态与人工中断、n8n、FastAPI、工具白名单/单退货编号隔离、四轮上限、请求超时、计算证据独立输出。日期采用业务当地日历日期，不计算小时级期限；示例14天含边界，仅内部合成检查。

暂不需要Dify、独立LangChain、RAG/向量/全文检索（小型结构化资料）、Redis/对象存储（不读取照片）、队列/数据库/容器反向代理（本地单任务演示）。内存检查点重启丢失，单worker、串行处理，繁忙429。共享密钥面向受信任操作员，reviewer自报姓名。

后续按需增加持久状态、身份权限、请求幂等、异步队列、文档存储、观测评估、备份恢复。没有真实订单和照片接入，没有退款或拒绝客户权利工具。所有建议由人工确认，政策基线需业务负责人维护。

[Skill](SKILL.md) · [检查记录](CHECKS.md)。源码MIT，模型及第三方依赖保留上游许可。
