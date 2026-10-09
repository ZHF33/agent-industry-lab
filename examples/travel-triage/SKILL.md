---
name: travel-document-triage
description: Triage structured travel-document exceptions using read-only evidence tools and human review.
---

# Travel document triage

Use for travel-office operators reviewing already-extracted, synthetic or locally authorized case JSON. Do not upload passenger files to external services.

Input: array of cases containing case_id, pnr, passenger_name and documents. Follow README.md. Run from this directory:

```powershell
python triage.py sample.json --output ../../runtime/travel-skill-demo.json
```

Choose a new output filename; never overwrite source or an existing report. Inspect the JSON report and CSV exception queue. Preserve tool_trace and source fields. Report missing itinerary, name differences, duplicate hashes, ambiguous candidates and insufficient information; uncertain matches go to a human.

Default execution is a rule prototype. Only use --model with an existing locally authorized Ollama model. Do not claim model or platform validation from mock tests. No booking, data correction, deletion, messaging or publishing. Human review remains required even when no exception is detected.

Acceptance: pytest test_triage.py -q; synthetic fixtures must remain unchanged. For real Agent status, additionally require actual model tool-call traces. This release has 16 passing offline tests, no real-model verification.
