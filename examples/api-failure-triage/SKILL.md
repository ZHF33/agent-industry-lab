---
name: api-failure-triage
description: Classify synthetic HTTP and transport failures with write-outcome uncertainty and human review.
---

Follow README; submit synthetic observations only. Inspect method, status and deterministic failure_report. Timeout is not proof of business failure. Reconcile writes before resubmission; GET/HEAD retry candidates still need policy review. Preserve thread_id for human approve/reject. Never execute retries, change permissions/credentials or send messages. Keep secrets and traces local; do not start services unless requested.
