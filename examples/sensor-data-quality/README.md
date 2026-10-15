# 传感器数据质量调查 Agent

面向数据平台值班人员：出现异常数值与采样断更时，核对数据契约、读取样本、计算质量问题，再给人工调查建议。数据异常不代表设备故障，不用于工业安全控制。

输入case_id、feed_id、description，见sample.json。合成示例期望60秒更新，快照12:03，最新记录12:01且数值999，计算工具输出invalid_range与stale_or_missing。范围仅为合成数据契约，不是设备安全阈值。未来时间、单位不同也会单独标记。

流程：n8n提交 → FastAPI → LangGraph自主工具调用 → 契约/读数/质量工具 → 人工中断 → n8n审核 → 恢复记录。输出thread_id、quality_report、证据与建议；approve只记录接受建议，不控制设备、不更改阈值、不静音告警、不发消息。

## 启动与集成

Python3.12+、本地Ollama/qwen3:4b，在本目录：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:SENSOR_API_KEY = '替换为本地随机密钥'
.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8098 --workers 1
```

POST /triage，X-API-Key头，请求体sample.json。人工核对后POST /threads/{thread_id}/review，正文 `{"decision":"approve","reviewer":"demo-reviewer"}`，或reject。

导入n8n-workflow.json，保持停用。Webhook配置独立Header Auth入口凭据，HTTP节点配置Header Auth（X-API-Key，与环境变量一致）。提交路径sensor-quality-case，审核路径sensor-quality-review；审核体含thread_id、decision、reviewer。API默认127.0.0.1:8098，Docker需改实际可达地址。状态码与结果转发，断网/超时终止，不盲目自动重复提交。

## 基建选择

采用Ollama、严格输入契约、LangGraph状态与人工中断、n8n、FastAPI密钥、受限工具、四轮上限、120秒模型超时和510秒HTTP等待。观测快照固定，按带时区时间比较，不推断设备故障原因。

暂不需要Dify、独立LangChain、RAG/全文/向量检索（固定结构数据）、Redis/对象存储（无大文件/缓存）、队列/数据库/容器反向代理（短演示任务）。状态为内存，重启丢失，单worker、串行处理，繁忙429。未来增加持久化、幂等、身份授权、异步队列、观测评估和备份恢复。共享密钥不区分个人身份，reviewer为自报姓名。

不访问真实传感器；新鲜度依据最近非未来记录，与数值有效性分开。没有验证采样丢点率、重复点、漂移和设备校准，不以有限范围检查替代完整质量评估。[Skill](SKILL.md) · [工程记录](CHECKS.md)。源码MIT，模型及依赖沿用上游许可。
