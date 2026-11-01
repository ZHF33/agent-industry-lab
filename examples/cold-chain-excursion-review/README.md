# 冷链温度异常审查 Agent

面向工业材料收货与运输运营：把混合摄氏/华氏记录、采样间隔与合成流程阈值放到同一份证据报告，减少人工逐行核查。仅使用虚构工业材料，阈值不代表任何真实产品标准。

输入：`case_id`、`shipment_id`、带时区且整秒的`as_of`、`description`。输出：异常采样点、统一单位后的峰值、短间隔保持值估算、未知时长、来源、模型工具轨迹及待人工复核建议。

## 流程

n8n提交 → FastAPI校验/鉴权 → LangGraph模型自主选工具 → 工具执行并反馈 → 模型解释异常和证据不足 → 人工approve/reject。

模型最多4轮、每轮3工具；lookup_shipment、lookup_readings、assess_excursion均成功并引用source后才送审。工具参数只允许当前运单ID，不能传外部URL或执行命令。超过预算/模型失败返回错误，不产生完成报告。

样例的50°F等于10°C。12:05–12:10按左端读数保持估算超上限300秒；12:10–12:20超过300秒采样间隔上限，全部列未知600秒，不插值成持续超温。两个超范围采样点不等于完整暴露历史；审核者需核原始记录、设备状态及真实产品政策。本例不计算货物劣化、不判断安全性、不放行货物。

## 运行

前提：Python 3.11+、用户自行准备的Ollama服务及支持工具调用的模型。以下命令由使用者手动执行：

```powershell
cd examples/cold-chain-excursion-review
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:COLD_CHAIN_API_KEY = Read-Host '本地API密钥'
$env:OLLAMA_MODEL = 'qwen3:4b'
.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8112 --workers 1
```

另一终端，进入同一目录：

```powershell
$headers = @{'X-API-Key' = Read-Host '同一本地API密钥'}
$case = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8112/triage -Headers $headers -ContentType application/json -Body (Get-Content sample.json -Raw -Encoding UTF8)
$case | ConvertTo-Json -Depth 20
$review = @{decision='approve'; reviewer='demo-reviewer'} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8112/threads/$($case.thread_id)/review" -Headers $headers -ContentType application/json -Body $review
```

验收预期：报告`estimated_above_seconds=300`、`unknown_seconds=600`及两个超范围采样点；`release_authorized=false`、`actions_executed=false`。人工approve只接受分析建议，不改变运单或设备。

[n8n工作流](n8n-workflow.json)保持inactive。导入后两个Webhook配置Header Auth，两个HTTP节点配置`X-API-Key`凭据；先用test webhook，不自动激活。容器中的127.0.0.1不是宿主机，按受控网络修改API地址；审核入口传返回的UUID thread_id、decision、reviewer。没有真实运输系统连接。

## 工程选择

LangGraph负责状态循环/人工暂停；n8n只转发业务触发。固定小型遥测表无需RAG或Dify知识工作流；直接Ollama接口无需额外LangChain适配。单worker、回环地址、内存检查点，重启需要重新提交。共享API密钥不等于审核者身份认证。

手动测试命令：`.\.venv\Scripts\python.exe -m unittest -v test_tools test_graph`。范围及基础设施评估见[CHECKS.md](CHECKS.md)，复用入口[SKILL.md](SKILL.md)。原创源码MIT，第三方依赖保留各自许可。
