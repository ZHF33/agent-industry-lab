# Architecture
The current V2 runtime uses HTTP webhooks to call the Agent API. Dify supplies configured workflow outputs. Local context assembly is keyword/structured knowledge handling, not evaluated vector RAG. Human review gates operations.

CLI entry: scripts/run_content_operation.py. Workflow entry: n8n/workflows/v2_full_content_pipeline_webhook.json.

Steps: n8n/workflows/v2_image_selection_webhook.json, n8n/workflows/v2_publish_draft_webhook.json, n8n/workflows/v2_publish_record_webhook.json, n8n/workflows/v2_publish_mock_webhook.json (mock only).
