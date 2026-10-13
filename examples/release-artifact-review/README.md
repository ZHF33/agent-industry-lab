# 发布包完整性复核 Agent

面向发布工程师：提交包与批准清单不一致时，查基线、查实际制品，计算SHA-256差异，整理带来源的人工复核建议。合成样例包含正常app.txt、改动的config.txt及多余extra.txt。完整性不等于发布者身份可信，也不等于没有恶意代码。

## 流程

`n8n发布复核入口 → FastAPI → LangGraph模型选工具 → 清单/制品/哈希核对 → 人工暂停 → n8n审核入口 → 恢复并记录审核`。

输入case_id、release_id、description，见sample.json。输出thread_id、integrity_report、建议及来源。三个只读工具核对相同、多余、缺失和哈希不一致，模型负责解释、人工负责确认基线来源；approve只接受复核建议，不批准生产上线。程序不读取本机路径、不签名、不部署、不删除文件。

## 运行

Python3.12+、Ollama/qwen3:4b；进入本目录：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:RELEASE_API_KEY = '替换为本地随机密钥'
.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8096 --workers 1
```

POST `/triage`，头X-API-Key，正文sample.json。保留thread_id，人工复核后POST `/threads/{thread_id}/review`，正文 `{"decision":"approve","reviewer":"demo-reviewer"}`，或decision=reject。

导入n8n-workflow.json，默认停用。两个Webhook节点配置Header Auth入口凭据；两个HTTP节点配置Header Auth API凭据（X-API-Key，与环境变量一致）。提交路径release-artifact-case，审核路径release-artifact-review；审核正文包含thread_id、decision、reviewer。API默认127.0.0.1:8096，Docker内改实际可达地址。凭据不写进导出文件。API状态码和正文原样返回，断网/超时终止，不盲目重复提交。

## 基建选择

使用：Ollama、严格JSON契约、LangGraph状态/工具循环/人工中断、n8n集成、FastAPI密钥、工具白名单和单发布编号隔离、hashlib计算、来源校验、四轮上限、120秒模型请求超时与510秒HTTP等待。内存检查点、单worker、串行处理，繁忙429。

暂不需要：Dify和独立LangChain适配（模型直接接入）；RAG/全文/向量检索（固定结构化清单）；对象存储/Redis/队列（内置短合成字节数据）；生产数据库/容器反向代理（本地演示）。后续按需求增加制品存储、持久状态、请求幂等、身份权限、观测评估、备份恢复。

当前假定基线可信，没有数字签名验证；数据全在源码中，不访问真实发布包。字节哈希按原始内容比较，不规范化换行。服务重启丢检查点，共享密钥面向受信任操作员、reviewer自报姓名。提交没有去重；审核不执行任何发布动作。

[Skill](SKILL.md) · [工程记录](CHECKS.md)。源码MIT，上游模型/依赖保留许可。官方资料核查2026-10-13：[Python hashlib](https://docs.python.org/3/library/hashlib.html)。
