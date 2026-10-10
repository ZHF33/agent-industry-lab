---
name: maintenance-ticket-triage
description: Run read-only maintenance ticket triage on synthetic records using a local Ollama model and review tool evidence.
---

1. Use synthetic JSON with ticket_id, equipment_id and description. Never load real plant records, secrets or customer information into this showcase.
2. Confirm local Ollama and qwen3:4b are available. Do not use cloud endpoints or paid services.
3. From the repository root run `python examples/maintenance-triage/agent.py examples/maintenance-triage/sample.json --output runtime/maintenance-result.json`; choose a new output filename.
4. Inspect tool_trace, cited_sources and advice_untrusted. Human review is mandatory. Sources validate provenance only, not correctness of suggested repairs.
5. Errors, missing data or model round limit mean incomplete processing. Never present a failed run as verified.
6. Do not execute repairs, restart equipment, change tickets or send notifications. Keep generated outputs local; publish source and sanitized verification summaries only.

## LangGraph and n8n integration

- Use graph_agent.py for the bounded model/tools loop and interrupt-based human review. Use api.py for POST /triage and POST /threads/{thread_id}/review.
- Follow the README to configure MAINTENANCE_API_KEY and import n8n-workflow.json. Configure Header Auth credentials in n8n; never place secrets in exported workflows.
- Submit synthetic tickets only. Preserve the returned thread_id and have a human explicitly choose approve or reject. Approval records a review, not permission to operate equipment.
- In-memory checkpoints are lost on server restart. Use one API worker. Do not automatically retry ambiguous submissions, and do not start services unless requested.
