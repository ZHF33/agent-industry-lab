# n8n HTTP workflows
Import JSON under workflows/ after configuring a private Agent API token and webhook secret. Templates are inactive and exclude runtime pinned data and saved credentials.
The primary entry is v2_full_content_pipeline_webhook.json calling Agent API /pipeline. No Execute Command or legacy placeholder workflow is distributed. n8n uses HTTP to the independent Python service.
Configure private credentials/URL and validate target-instance execution before activation. Real publishing is not implemented.
