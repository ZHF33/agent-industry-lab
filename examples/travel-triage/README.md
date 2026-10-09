# Travel Document Exception Triage

旅行文档异常分诊精简版。输入已抽取的脱敏 JSON，输出异常队列 JSON/CSV 和工具证据；不读取原始旅行文件，不修改资料，不发送消息。

**已验证：规则原型。** 提供本地 Ollama 工具调用入口，最多三轮；真实模型、LangGraph、n8n/Dify 平台接入尚未验证，未实现 OCR 或 RAG。无异常不代表可出行，仍需人工审核。

Python 3.12+，运行无第三方依赖。在本目录执行：

```powershell
python triage.py sample.json --output ../../runtime/travel-demo.json
```

输出文件必须不存在。支持缺行程单、姓名差异、重复哈希、多个候选、信息不足。姓名比较仅做 Unicode/空白/大小写归一化，音译差异留给人工。

已有本地 Ollama 和支持工具调用的模型时，可加 `--model YOUR_LOCAL_MODEL`。只访问 localhost，不下载模型；模型失败会终止，不伪装成功。模型仅选择工具，必需检查由规则兜底，结论引用真实工具输出。

字段：`case_id`、`pnr`、`passenger_name`、`documents[]`；文档字段为 `document_id`、`kind`、`pnr`、`passenger_name`、可选 `sha256`。`kind=itinerary` 表示行程单。哈希由上游提供，本程序不访问文件路径。实际业务应补充抽取质量校验与身份/权限隔离。

验证：六类各两个合成样例，另测轮数上限、模型虚假批准、非法输入、关联信息缺失；mock 仅测循环逻辑，不算真实模型验证。

```powershell
python -m pytest test_triage.py -q
```

## Skill entry

[SKILL.md](SKILL.md) provides the reusable operator instructions, safe execution command and evidence requirements. It wraps the existing runnable prototype; adding this entry does not imply real-model or platform verification.
