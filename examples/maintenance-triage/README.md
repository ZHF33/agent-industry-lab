# 设备维修工单分诊 Agent

面向维修主管：查设备资料、手册及历史记录，整理带来源的人工审核建议。全部输入与知识为合成数据；不连接工厂，不控制设备，不派单。

## 运行

### LangGraph + n8n 流程

`n8n 工单入口 → HTTP API → LangGraph 模型/工具循环 → 暂停审核 → n8n 审核入口 → 恢复 LangGraph → 返回审核记录`。

[graph_agent.py](graph_agent.py) 管理状态、四轮模型上限和人工中断；[api.py](api.py) 提供工单及审核接口；[n8n-workflow.json](n8n-workflow.json) 包含两条入口。原有 [agent.py](agent.py) 保留工具与模型适配以及独立命令行运行。

在本目录创建虚拟环境并安装依赖：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:MAINTENANCE_API_KEY = '替换为本地生成的随机密钥'
.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8092 --workers 1
```

模型仍使用本地 Ollama/qwen3:4b。这里只提供运行步骤，不自动启动服务。API密钥不得提交GitHub。

将工作流JSON导入n8n，保持停用。在两个Webhook节点分别选择Header Auth凭据，在两个HTTP Request节点选择Header Auth凭据，API凭据头名为 `X-API-Key`，值与环境变量一致。Webhook使用独立入口密钥。凭据在n8n中配置，不包含在导出文件里。HTTP节点默认访问127.0.0.1:8092；n8n与API在同一主机时可用，Docker内应改为实际可达地址，并配置受控网络访问。

提交入口 `maintenance-ticket` 接收 sample.json 的三个字段；响应包含 thread_id、pending_review 和 result。人工核对建议后，通过 `maintenance-review` 提交 `thread_id`、`decision`（approve/reject）、`reviewer`。审批只记录是否接受建议，不执行维修、不发送消息。API非成功状态由工作流原样返回；连接中断或HTTP超时会终止该次工作流，勿盲目自动重试提交。

检查点使用内存，单进程运行，重启会丢失待审核状态；共享API密钥代表受信任演示操作员，reviewer是自报姓名。服务串行处理任务，繁忙返回429。当前请求同步等待模型，工作流HTTP超时510秒；上游网关必须匹配等待时间。提交请求未实现重复请求去重，网络结果不确定时需要人工确认，生产接入应增加持久检查点、身份权限、幂等和任务队列。

### 独立命令行

Python 3.12+；独立命令行仅用标准库。安装 Ollama 后执行 `ollama pull qwen3:4b`。在仓库根目录运行：

```powershell
python examples/maintenance-triage/agent.py examples/maintenance-triage/sample.json --output runtime/maintenance-result.json
```

输出必须为新文件。模型在 localhost:11434 运行；需要约2.5GB模型下载，运行内存需求高于模型文件大小。离线运行无需云模型密钥或付费服务。

模型自主选择三个只读工具，并读取返回结果后给出建议。四轮上限、每轮三次工具调用、120秒请求超时、工具白名单、设备编号边界与来源引用校验。失败明确报错，无规则成功兜底。`advice_untrusted` 是待人工核对的模型文本，来源出现不证明建议正确，程序不会执行建议。输出状态固定为人工审核。

现有不足：内置极小合成知识库；手册按设备精确查找，不是语义RAG。未实现提示注入抵御证明、语义安全验证、完整追踪平台、生产权限、多用户隔离或认证。原始工具轨迹仅保留本地，GitHub只发布验证摘要。

## 基建取舍

已使用：Ollama模型推理、JSON输入校验、工具适配器、受控编排、超时与人工审核边界。业务记录只读，暂不需要数据库状态、Redis缓存限流、对象存储、异步队列、写操作幂等及备份恢复。极小知识使用精确查询，暂不需要向量检索。独立本地CLI暂不需要容器反向代理或认证密钥；生产接入前必须补权限及审计。

验证见 [VERIFICATION.md](VERIFICATION.md)，操作入口见 [SKILL.md](SKILL.md)。源码遵循仓库MIT许可；Ollama与Qwen3分别遵循上游许可，模型不上传。

官方资料（核查2026-10-09）：[工具调用](https://docs.ollama.com/capabilities/tool-calling)、[Qwen3模型及Apache-2.0许可](https://ollama.com/library/qwen3:4b)。
