---
name: supplier-quote-review
description: Compare synthetic supplier quotes using read-only tools and precise cost calculations before human review.
---

1. Follow README configuration. Submit synthetic case_id, rfq_id and description only.
2. Inspect inquiry, quote sources and deterministic cost_comparison. Compare the same currency and unit; missing freight is unknown, not zero.
3. Confirm pre-tax cost scope and lead time. Cheapest unit price does not imply cheapest total or an acceptable supplier.
4. Preserve thread_id. A human may approve or reject through the review endpoint. Never order, pay or contact suppliers.
5. Do not automatically retry ambiguous submissions. Keep credentials and traces local. Do not start services unless requested.
