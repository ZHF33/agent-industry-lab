---
name: sensor-data-quality-review
description: Investigate synthetic sensor feed freshness, units and ranges with read-only tools and human review.
---

Submit synthetic cases following README. Inspect feed contract, readings and quality_report separately. Stale or invalid readings do not establish equipment failure or safety. Preserve thread_id for human approve/reject. Never operate equipment, change limits, silence alarms or send messages. Keep keys and traces local; do not start services or repeat ambiguous submissions automatically.
