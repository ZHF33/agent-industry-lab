# 设备维修工单分诊 Agent

面向维修主管：查设备资料、手册及历史记录，整理带来源的人工审核建议。全部输入与知识为合成数据；不连接工厂，不控制设备，不派单。

## 运行

Python 3.12+；源码仅用标准库。安装 Ollama 后执行 `ollama pull qwen3:4b`。在仓库根目录运行：

```powershell
python examples/maintenance-triage/agent.py examples/maintenance-triage/sample.json --output runtime/maintenance-result.json
```

输出必须为新文件。模型在 localhost:11434 运行；需要约2.5GB模型下载，运行内存需求高于模型文件大小。离线运行无需云模型密钥或付费服务。

模型自主选择三个只读工具，并读取返回结果后给出建议。四轮上限、每轮三次工具调用、120秒请求超时、工具白名单、设备编号边界与来源引用校验。失败明确报错，无规则成功兜底。`advice_untrusted` 是待人工核对的模型文本，来源出现不证明建议正确，程序不会执行建议。输出状态固定为人工审核。

现有不足：内置极小合成知识库；手册按设备精确查找，不是语义RAG。未实现提示注入抵御证明、语义安全验证、完整追踪平台、生产权限、多用户隔离或认证。原始工具轨迹仅保留本地，GitHub只发布验证摘要。

## 基建取舍

已使用：Ollama模型推理、JSON输入校验、工具适配器、受控编排、超时与人工审核边界。业务记录只读，暂不需要数据库状态、Redis缓存限流、对象存储、异步队列、写操作幂等及备份恢复。极小知识使用精确查询，暂不需要向量检索。独立本地CLI暂不需要容器反向代理或认证密钥；生产接入前必须补权限及审计。观测当前仅本地输出，评估仅有限合成验收；Dify、n8n、LangChain/LangGraph未接入也未验证，有集成需求后再引入。

验证见 [VERIFICATION.md](VERIFICATION.md)，操作入口见 [SKILL.md](SKILL.md)。源码遵循仓库MIT许可；Ollama与Qwen3分别遵循上游许可，模型不上传。

官方资料（核查2026-10-09）：[工具调用](https://docs.ollama.com/capabilities/tool-calling)、[Qwen3模型及Apache-2.0许可](https://ollama.com/library/qwen3:4b)。
