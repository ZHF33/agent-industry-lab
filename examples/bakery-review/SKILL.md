---
name: bakery-content-review
description: Review bakery content against explicit product facts and channel limits, preserving human approval and traceable issues.
---

# Bakery content review

Use with product facts, full proposed copy and a channel character limit.

1. Collect product name, ingredients, storage and explicit claims. Never invent facts.
2. Attach claims to exact fact keys/values. Evidence matching does not prove semantic support.
3. Generate a unique revision job_id and call the locally configured POST `/reviews` using README.md's schema. Do not transmit private data to unapproved endpoints.
4. Show issues, evidence and full copy to the operator. Missing facts, mismatches or overlength require revision. Issue-free output still needs human review.
5. Only after explicit confirmation, record POST `/reviews/{job_id}/decision` with the actual reviewer and note. Never fabricate approval or publish.
6. Preserve job_id for audit history. Unknown facts and undeclared claims remain human-review items.

Start the local FastAPI service as documented. These deterministic checks are not an autonomous model Agent. Platform and model integration require separate validation.
