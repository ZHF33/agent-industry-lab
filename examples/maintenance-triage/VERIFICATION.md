# 验证记录

## 2026-10-10 源码增量检查

新增LangGraph状态图、内存检查点、人工中断与恢复、带密钥的HTTP接口、n8n工单与审核入口。使用Python AST检查源码语法，JSON解析检查工作流格式、六个节点及连接引用；工作流active=false。按用户要求未启动模型、API或n8n，也未运行项目测试。本节不改变下面旧版命令行的实际运行记录。依赖顶层版本固定，传递依赖由安装器解析。

2026-10-09，本机 Windows、Ollama 0.40.2、qwen3:4b（digest 359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7）。

## 真实模型验收

在仓库根目录执行 README 的命令，使用内置合成样例。实际结果：三轮完成。第一轮模型自主调用 lookup_equipment、search_manual、lookup_history；程序执行三个只读工具并将结果返回模型。后续模型先遗漏来源，经上限内的来源反馈后输出引用 manual-demo-01 的建议：合格技术人员能源隔离后检查皮带对齐；历史不证明当前原因，人工复核。

实际状态 human_review_required，actions_executed=false。工具结果及建议仅存本地 runtime/maintenance-real-01.json，不上传运行日志。上述为人工核对后的验证摘要，不代表所有输入可靠。

首次测试发现思考文本导致工具重复解析，已启用独立思考字段；来源遗漏会在四轮内请求修正，仍不满足则报错。模型输出不进行语义安全认证，不直接执行业务动作。

## 控制逻辑测试

```powershell
.\.venv\Scripts\python.exe -m pytest examples/maintenance-triage/test_agent.py -q
```

实际：8 passed。涵盖工具循环、未知工具、跨设备参数、缺参数、无工具提前结束、轮数上限、非法输入和缺引用。测试模型为 mock，仅验证程序边界。真实模型验收只有一个合成场景，不代表全面评估。

未验证：真实工厂数据、多用户安全、平台导入、Dify/n8n、生产部署与稳定性。所有建议必须由具备资格的人员审核。
