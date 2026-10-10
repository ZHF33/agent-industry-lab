---
name: inventory-discrepancy-investigation
description: Investigate synthetic inventory count discrepancies with read-only tools, exact arithmetic and human review.
---

1. Use synthetic case_id, sku and description. Follow README configuration; never publish keys or business records.
2. Submit to /triage using the configured X-API-Key; preserve thread_id.
3. Inspect stock snapshot, count source, movements and calculated difference. Pending movement is a hypothesis, not a proven cause. Confirm same time and unit.
4. An authorized human may submit approve/reject to the review endpoint. Approval records review only; do not adjust inventory or send messages.
5. Unknown SKU, missing sources, busy API or ambiguous network result require manual follow-up. No blind automatic resubmission.
6. Keep generated traces local. Do not start services unless requested.
