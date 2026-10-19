# 告警重复与噪声复核 Agent

面向运维值班人员：收到多条相似告警时，区分重复投递与独立事件，再按服务、错误码和级别分组，给人工调查建议。相同类型不等于同一事故，工具不会自动静音或关闭告警。

流程：n8n批次入口 → FastAPI → LangGraph自主选择批次/事件/分组工具 → 人工中断 → n8n审核 → 恢复记录。输入case_id、batch_id、description，见sample.json。输出thread_id、grouping_report、证据与建议。示例4条投递、3个唯一事件、1条重复，形成2个组。approve仅接受复核建议，不处理真实告警。

## 运行入口

Python3.12+、Ollama/qwen3:4b；在本目录：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:ALERT_API_KEY = '替换为本地随机密钥'
.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8102 --workers 1
```

POST /triage，X-API-Key头，正文sample.json；保存thread_id。人工复核后POST /threads/{thread_id}/review，正文 `{"decision":"approve","reviewer":"demo-reviewer"}` 或reject。

导入n8n-workflow.json，默认停用。Webhook配置独立Header Auth入口凭据；HTTP节点配置Header Auth（X-API-Key与环境变量一致）。提交路径alert-noise-case，审核路径alert-noise-review，审核体含thread_id、decision、reviewer。默认API127.0.0.1:8102，Docker内须改可达地址。凭据不嵌入JSON；状态码/正文转发，断网超时终止，不自动重提。

## 分组口径与基建

事件身份为固定批次内event_id；内容口径仅service/code/severity，不包括描述、时间等其他字段。相同编号同内容判重复投递，同编号不同内容标冲突并从分组计数中排除该编号。重复计数为与该编号首条内容一致的后续投递次数，不包含冲突记录；它不保证与组计数相加等于原始条数。实际平台应定义来源、租户、时间窗与完整内容契约，不能直接套用当前简化键。

采用Ollama、严格JSON契约、LangGraph状态/人工中断、n8n、FastAPI密钥与串行锁、Counter计数、工具白名单、四轮上限、120秒模型超时和510秒HTTP等待。内存检查点重启丢失、单worker、繁忙429；共享密钥只面向受信任操作员，reviewer自报姓名。

暂不需要Dify/独立LangChain/RAG全文向量（固定结构数据）、Redis/对象存储（小批次，无大文件）、队列/数据库/反向代理（本地演示）。跨批次去重、长期存储、并发任务、幂等提交、身份授权、观测评估及备份恢复留作后续按需接入。不存在真实监控平台、根因判断、通知或告警抑制工具。[Skill](SKILL.md) · [工程记录](CHECKS.md)。源码MIT，上游依赖和模型保留许可。
