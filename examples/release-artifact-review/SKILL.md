---
name: release-artifact-integrity-review
description: Compare synthetic release manifests and artifact digests, then request human review without deployment.
---

1. Submit synthetic case_id, release_id and description according to README. Never send file paths, keys or real release packages.
2. Inspect manifest, artifact list and integrity_report. Treat match as byte integrity only, not publisher authenticity or malware clearance.
3. Human review must confirm the baseline source, unexpected/missing artifacts and mismatches. Preserve thread_id for approve/reject.
4. Approval accepts review advice only. Never deploy, sign, delete, publish packages or send business messages.
5. Keep traces and credentials local. Do not blindly repeat ambiguous submissions or start services unless requested.
