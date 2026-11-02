# 供应商附件接收审查 Agent

面向采购资料接收与文档平台运营：核查一个批次附件清单中的路径、声明大小和类型，形成带来源的异常建议与人工复核单，减少逐行筛查。只读合成元数据，不接收或打开真实附件。

输入：case_id、batch_id、带时区as_of、description。输出：逐附件异常理由、批次声明总大小、内容/恶意软件状态未知、模型工具轨迹与待人工建议。

## 流程

n8n提交 → FastAPI鉴权校验 → LangGraph模型选择lookup_batch、lookup_manifest、assess_intake → 读取工具结果并解释 → 人工approve/reject。

四轮上限，每轮最多三工具；三个工具成功、建议含source后才进入人审。路径采用严格ASCII相对名契约：拒绝上级目录、绝对/驱动器路径、反斜线、编码/冒号、特殊设备名等；按合成政策检查扩展名、声明类型、单文件和批次大小。无异常只表示元数据规则未发现问题，不保证文件内容、扫描或真实落盘安全。

## 运行

前提：Python3.11+，用户自行准备Ollama服务和支持工具调用的模型。手动执行：

```powershell
cd examples/attachment-intake-review
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:ATTACHMENT_API_KEY = Read-Host '本地API密钥'
$env:OLLAMA_MODEL = 'qwen3:4b'
.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8113 --workers 1
```

另一终端进入同一目录：

```powershell
$headers = @{'X-API-Key' = Read-Host '同一本地API密钥'}
$case = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8113/triage -Headers $headers -ContentType application/json -Body (Get-Content sample.json -Raw -Encoding UTF8)
$case | ConvertTo-Json -Depth 20
$review = @{decision='approve'; reviewer='demo-reviewer'} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8113/threads/$($case.thread_id)/review" -Headers $headers -ContentType application/json -Body $review
```

样例预期：ATT-2上级路径异常；ATT-3声明大小超限且扩展名/类型不匹配；两个异常附件，总声明6002148字节。ATT-1元数据无异常，但content_verified=false、malware_status=unknown。人审只接受报告，不移动、删除、下载、解压或导入文件。

[n8n工作流](n8n-workflow.json)保持inactive。导入后两个Webhook设置Header Auth，两个HTTP节点设置`X-API-Key`凭据，先用test webhook。容器部署按受控网络修改API地址；审核入口传返回的UUID thread_id、decision、reviewer。工作流只转发清单请求，不处理文件字节。

## 选择与边界

LangGraph负责模型工具循环与暂停；n8n转发业务入口。小清单精确查表无需Dify/RAG或向量检索；直接Ollama接口无需额外LangChain适配。路径判断不访问文件系统，没有病毒扫描、内容嗅探、沙箱或文件落盘。真实接收服务需另做身份、隔离、大小限制与安全打开，不应直接把清单路径拼到硬盘上。

单worker回环服务、内存检查点，重启需重提；共享密钥与reviewer文字不是完整身份认证。手动验收：`.\.venv\Scripts\python.exe -m unittest -v test_tools test_graph`。实际检查及基础设施评估见[CHECKS.md](CHECKS.md)，复用入口[SKILL.md](SKILL.md)。原创代码MIT，第三方依赖保留许可。
