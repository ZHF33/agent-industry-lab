# Bakery Content Review Skill

Input: product facts, explicit claims with evidence keys/values, full copy and channel character limit. Output: traceable issues, evidence, human checks, pending-review status. Missing ingredients/storage, evidence mismatch and overlength block approval. Exact evidence equality does not establish that the prose logically follows from the fact; full semantic review remains human.

POST `/reviews`; repeat identical job_id is idempotent, changed input returns 409. GET `/reviews/{job_id}`. POST `/reviews/{job_id}/decision` records a human decision with reviewer and note; unresolved issues return 422. Decisions are terminal; submit a new ID for revisions. All persistence is local SQLite.

## Sample request

```json
{"job_id":"bakery-demo-001","product":{"name":"Beef ciabatta","facts":{"ingredients":"beef, wheat","storage":"refrigerate"}},"claims":[{"text":"Made with beef","fact_key":"ingredients","fact_value":"beef, wheat"}],"copy":"Beef ciabatta","max_chars":100}
```

## n8n

Import `integrations/n8n/bakery-review.json` as an inactive manual workflow. Start the API; HTTP URL defaults to `http://host.docker.internal:8091/reviews` for Docker Desktop n8n. Host-based n8n uses `http://127.0.0.1:8091/reviews`. Docker access requires a host binding reachable by containers and access restrictions before real use. Execute manually; inspect pending-review JSON. No publishing or approval node is present. HTTP errors fail execution, timeout 10s, no unbounded retries.

## Dify

Use an existing Workflow with input fields for product facts and copy. A Knowledge Retrieval node retrieves product sources; an LLM node produces explicit claims with fact keys and citations; an HTTP node calls this API with the schema above. Preserve full copy for human review. Configure the host URL for Dify's actual network; do not disable its SSRF protection to make localhost access work. This recipe is not an imported or executed Dify DSL. A target-instance export/import and execution is still required for platform verification.
