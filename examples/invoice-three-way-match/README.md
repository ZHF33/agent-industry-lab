# 采购订单、收货单与发票三单复核 Agent

面向应付账款复核人员：订单10件、收货8件、发票10件，金额算对仍需调查数量差异。读取三类合成单据，工具计算身份、数量、币种、单价和税前行金额差异，模型整理带来源建议，交人工审核；不付款、不记账、不修改单据。

流程：n8n提交 → FastAPI → LangGraph自主选择订单/单据/匹配工具 → 人工暂停 → n8n审核 → 恢复记录。输入case_id、invoice_id、description，见sample.json；输出thread_id、matching_report、建议和来源。approve只记录接受建议，不是付款授权。仅单商品行，不处理税务、运费、折扣、多批收货、退货或汇率。

## 运行

Python3.12+，本地Ollama/qwen3:4b；在本目录执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:INVOICE_API_KEY = '替换为本地随机密钥'
.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8099 --workers 1
```

POST /triage，X-API-Key头，正文sample.json。保留thread_id，人工复核后POST /threads/{thread_id}/review，正文 `{"decision":"approve","reviewer":"demo-reviewer"}` 或reject。

导入n8n-workflow.json，默认停用。Webhook配置独立Header Auth凭据；HTTP节点配置Header Auth，头X-API-Key与环境变量相同。提交路径invoice-match-case，审核路径invoice-match-review，审核体含thread_id、decision、reviewer。默认API127.0.0.1:8099，Docker需改实际可达地址。凭据不嵌入工作流，非成功HTTP状态转发，断网/超时终止，不自动重复提交。

## 基建取舍

采用Ollama模型、JSON契约、LangGraph状态与人工中断、n8n、FastAPI密钥与串行锁、Decimal精确金额、工具白名单/单发票范围、四轮上限、120秒模型请求超时、510秒HTTP等待。数量限制为正整数件数，金额非负且有限；计算行总价不自动舍入，按合成契约精确比较。币种不一致时不比较单价；商品或单位不一致的结果须先人工解决，不能把数量告警直接用于付款判断。

暂不需要Dify/独立LangChain/RAG全文或向量检索（结构化单行数据）、Redis/对象存储（无大文件/缓存）、队列/数据库/容器反向代理（单任务本地入口）。内存检查点重启丢失，必须单worker，繁忙429；共享密钥只面向受信任人员，reviewer自报姓名。

后续按业务增加OCR和来源定位、持久检查点、身份授权、提交幂等、异步队列、观测评估和备份恢复。单据缺失或数量口径变化不等于欺诈；真实会计、税务与付款审批由专业人员执行。源码MIT，上游模型/依赖保留许可。[Skill](SKILL.md) · [工程记录](CHECKS.md)。
