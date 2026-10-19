# 工程记录

2026-10-19：AST语法、JSON连接引用及人工逻辑检查，不启动Ollama/API/n8n，不执行测试。顶层依赖沿用固定版本，传递依赖由安装器解析。

检查batch_id、ALERT_API_KEY、8102、三个工具、四轮限制、人工恢复、n8n active=false。Counter作用于去重且排除冲突后的事件，不按投递条数直接统计。可选python -m unittest test_tools.py，预期4项通过，非实际结果。无平台/真实模型或生产执行证据。
