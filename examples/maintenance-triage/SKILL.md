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
