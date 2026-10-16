---
name: invoice-three-way-match
description: Reconcile synthetic purchase order, receipt and invoice evidence with exact calculations and human review.
---

Follow README; submit synthetic cases only. Inspect purchase-order identity, SKU, unit, currency, received quantity and deterministic matching_report before interpreting amounts. Preserve thread_id for human approve/reject. Missing receipt evidence is not fraud. Approval accepts advice, never authorizes payment, posting or tax treatment. Keep keys and traces local. Do not start services or blindly retry ambiguous submissions.
