# Bakery Agent

V2 核心源码精简版。

请求 → n8n → Agent API → Dify → 内容与图片提示词 → 人工审批 → 本地记录。

## 本地运行
在本目录执行：
```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe -m pytest -q --import-mode=importlib
.\.venv\Scripts\python.exe scripts/run_content_operation.py --mode dry-run --request "今日的爆品是牛肉恰巴塔，生成它的解构风展示图"
.\.venv\Scripts\python.exe scripts/run_v2_acceptance.py --base-dir runs/demo-acceptance --json
```

## 平台接入
- 将 `.env.example` 复制为 `.env`，本地填写独立 token、webhook secret 和 n8n encryption key。
- `docker compose up -d --build`；首次创建 n8n owner 账户。
- 导入 `n8n/workflows/v2_full_content_pipeline_webhook.json`，配置私有认证后手动启用。
- Dify 独立部署；导入 `dify/workflows/bakery_operation_v1.dify.yml`，配置可用模型、发布私有应用并填写 API key。
- 本地 API：`python scripts/agent_http_api.py --host 127.0.0.1 --port 8765`。

保留核心代码、审批、SQLite、Dify DSL、n8n HTTP 流程、测试和虚构知识样例。排除密钥、历史运行记录、数据库、图片、旧流程和缓存。

离线验收使用模拟文本、演示图片及本地发布记录，不向真实平台发布。工作流默认未启用，实机导入与模型调用待验证。n8n 固定为 2.42.4；示例依赖锁定。知识上下文组装不是已验证向量 RAG。[验证记录](docs/verification.md)

步骤模板：`n8n/workflows/v2_image_selection_webhook.json`、`n8n/workflows/v2_publish_draft_webhook.json`、`n8n/workflows/v2_publish_record_webhook.json`、`n8n/workflows/v2_publish_mock_webhook.json`（模拟发布）。
