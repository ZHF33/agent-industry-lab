# 网络访问申请复核 Agent

面向平台运维人员：收到访问申请后，核对目标IP、端口、协议和资产负责人，计算与演示策略的差异，再整理带来源的人工审核建议。仅使用合成资料，不扫描、不连接申请目标、不改防火墙。

流程：n8n提交 → FastAPI → LangGraph自主选择申请/策略/评估工具 → 人工暂停 → n8n审核 → 恢复审核记录。输入case_id、request_id、description，见sample.json；输出thread_id、access_report、工具轨迹与建议。approve仅接受复核建议，不授予访问权。

示例目标203.0.113.10:5432/tcp，演示策略只包含192.0.2.0/24的443/tcp，因此报告目标范围与端口不一致。地址只作合成文本，不发起请求。策略是固定合成白名单，不代表实际企业安全规范。

## 运行

Python3.12+、本地Ollama/qwen3:4b，在本目录：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:NETWORK_API_KEY = '替换为本地随机密钥'
.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8100 --workers 1
```

POST /triage，头X-API-Key，正文sample.json；保留thread_id。人工复核后POST /threads/{thread_id}/review，正文 `{"decision":"approve","reviewer":"demo-reviewer"}`，或reject。

导入n8n-workflow.json，默认停用。Webhook配置独立Header Auth入口凭据；HTTP节点配置Header Auth（X-API-Key，与环境变量一致）。提交路径network-access-case，审核路径network-access-review，审核正文包含thread_id、decision、reviewer。API默认127.0.0.1:8100，Docker须改实际可达地址并限制网络。凭据不嵌入导出文件，API状态/正文原样转发，超时或断网终止，不盲目重复提交。

## 基建取舍

采用Ollama模型、严格JSON契约、LangGraph状态与人工中断、n8n集成、FastAPI密钥、受限单申请工具、ipaddress纯文本运算、四轮上限、120秒模型超时和510秒HTTP等待。内存检查点重启丢失，单worker串行处理、繁忙429。共享密钥适合受信任演示人员，reviewer自报姓名。

暂不需要Dify/独立LangChain/RAG全文与向量检索（结构化小策略）、Redis/对象存储（无缓存/大文件）、队列/数据库/容器反向代理（本地单任务）；以后按需增加持久状态、身份对象授权、幂等、任务队列、观测评估、审计与备份恢复。

当前只核对字面IP、协议和端口，未处理域名解析、网络路径、来源网段、服务身份、策略优先级、有效期限或实际安全性。白名单匹配也不等于授权。工具没有网络扫描、防火墙或凭据发放能力。[Skill](SKILL.md) · [工程记录](CHECKS.md)。源码MIT，上游依赖/模型保留许可。官方资料核查2026-10-17：[ipaddress](https://docs.python.org/3/library/ipaddress.html)。
