# 物流延误调查 Agent

面向物流协调员：承诺送达时间已过，运单只有零散扫描记录。查询承诺时间与轨迹，由程序计算逾期，再让模型整理证据和人工调查建议。没有签收记录不等于确认未送达，枢纽扫描不等于查明延误原因。

## 流程与交付

`n8n运单入口 → FastAPI → LangGraph模型选工具 → 运单/事件/时间计算 → 人工暂停 → n8n审核入口 → 恢复并记录审核`。

输入case_id、shipment_id、description，见sample.json。合成快照UTC13:00、ETA为UTC12:00，评估逾期60分钟，签收状态待确认。工具将晚于快照的事件排除出评估；原始轨迹仍可查询。输出thread_id、delay_assessment、建议、引用来源及工具轨迹，人工核对承运商记录后决定调查动作。approve只记录建议审核，不改ETA、不调度、不赔付、不发客户消息。

## 运行

Python3.12+，本地Ollama/qwen3:4b；进入本目录：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:SHIPMENT_API_KEY = '替换为本地随机密钥'
.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8095 --workers 1
```

POST `/triage`，X-API-Key头，正文sample.json；保存thread_id。人工复核后POST `/threads/{thread_id}/review`，正文 `{"decision":"approve","reviewer":"demo-reviewer"}`，或decision=reject。

导入n8n-workflow.json，默认停用。Webhook节点配置Header Auth入口凭据；HTTP节点配置Header Auth API凭据，头名X-API-Key，与环境变量相同。提交路径shipment-delay-case，审核路径shipment-delay-review；审核正文含thread_id、decision、reviewer。默认API地址127.0.0.1:8095；Docker内需改实际可达地址并配置受控网络访问。API状态码/正文经工作流返回；断网或超时停止，不自动重复提交。

## 基建取舍

使用：Ollama推理、JSON契约、业务工具白名单与单运单参数隔离、LangGraph循环与人工审批、n8n集成、FastAPI密钥、四轮上限、120秒模型请求超时、510秒工作流HTTP超时、datetime带时区计算。合成快照固定，避免运行当天改变结果；UTC偏移必须明确，不能猜时区。模型建议不替代承运商事实。

暂不需要：Dify应用平台/独立LangChain（已有轻量接口）；RAG和向量/全文检索（小型结构化事件）；Redis/对象存储（无大文件和缓存）；队列与数据库（单任务演示）；容器反向代理（本地服务说明）。状态当前为内存检查点，重启消失，单worker、串行处理；繁忙返回429。

计划：接真实轨迹API前补身份权限、持久检查点、异步队列、提交幂等、观测评估及备份恢复。当前只读，不需要写库存/派车事务；共享密钥仅面向受信任操作员，reviewer自报姓名。请求未去重，结果不确定须人工核对；当前没有恢复失败模型节点的专门端点。

计算采用同一快照，整分钟向下取整；不足一分钟仍可能处于逾期状态。明确签收时间用于实际迟到评估，不能使用将来的签收时间。未实现节假日、工作日SLA、订单改约和承运商补录冲突处理。

[Skill](SKILL.md) · [工程记录](CHECKS.md)。源码MIT，模型和依赖遵循上游许可。官方资料核查2026-10-12：[datetime](https://docs.python.org/3/library/datetime.html)、[n8n HTTP节点](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/)。
