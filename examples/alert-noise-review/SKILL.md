---
name: alert-noise-review
description: Distinguish synthetic duplicate alert deliveries, conflicting event IDs and grouped observations before human review.
---

Follow README; use synthetic batch identifiers. Inspect event identity, payload scope, conflicting IDs and deterministic grouping_report. Same-type events do not prove one incident or root cause. Preserve thread_id for human approve/reject. Never suppress, close or route alerts, change thresholds or send notifications. Keep credentials and traces local. Do not start services or blindly retry ambiguous submissions.
