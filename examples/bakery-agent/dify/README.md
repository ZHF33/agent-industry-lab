# Dify Setup Notes

This folder contains workflow specifications, importable DSL files, and prompt blocks for Dify.

Do not connect directly to Dify internal databases. Create or import Dify workflows through the Dify UI, then configure providers and publish the app.

## Workflow Files

- `workflows/bakery_operation_v1.dify.yml`: GPT/OpenAI workflow for Phase 1.2 live text generation.
- `workflows/bakery_operation_v1.local_test.dify.yml`: provider-free workflow for local no-key end-to-end testing.
- `workflows/*.workflow.md`: manual workflow node specifications.
- `prompts/*.md`: reusable prompt blocks.

## Import Bakery GPT Workflow

1. Open Dify at `http://localhost:8080`.
2. Go to Studio / Apps.
3. Choose Import DSL / Import from DSL file.
4. Upload `workflows/bakery_operation_v1.dify.yml`.
5. Open the imported app and rename it to `Bakery AI Operation Agent V2` if Dify keeps the DSL's older display name.
6. Configure the OpenAI provider in Dify. The DSL uses `openai / gpt-4o-mini`.
7. Run a manual test with:
   - `product_query`: 牛肉恰巴塔
   - `campaign_goal`: 生成一套小红书和抖音待审核内容
   - `product_knowledge`: paste one processed product doc, or replace the formatter node with Knowledge Retrieval.
8. After your Dify Knowledge dataset is ready, replace `Knowledge Context Formatter` with a real Knowledge Retrieval node and pass its output into `Content Planner`.
9. Publish the app and create a service API key.
10. Put the API key into `.env` as `DIFY_API_KEY=...`, then restart n8n.

Stage 1 keeps media API calls as placeholders. The Dify workflow only generates image and video prompts.

Historical CHAGEE/tea examples in older notes are legacy local tests only. The active V2 production path is bakery-oriented and starts from the n8n content webhook or `scripts/run_content_operation.py`.

