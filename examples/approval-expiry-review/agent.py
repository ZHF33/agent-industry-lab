"""Synthetic approval evidence triage. Does not grant access or execute approvals."""
import json
import os
import urllib.request
from datetime import datetime, timezone

REQUESTS = {"REQUEST-DEMO-01": {
    "request": {"source": "access-request-demo-01", "request_id": "REQUEST-DEMO-01", "revision": 2,
                "action": "grant_read", "scope": "DEMO-DATASET-A", "observed_at": "2026-10-30T12:00:00+00:00"},
    "approval": {"source": "approval-demo-01", "request_id": "REQUEST-DEMO-01", "request_revision": 2,
                 "action": "grant_read", "scope": "DEMO-DATASET-A", "decision": "approve", "reviewer": "demo-owner",
                 "approved_at": "2026-10-30T11:50:00+00:00", "expires_at": "2026-10-30T12:00:30+00:00",
                 "revoked": False, "consumed": False, "observed_at": "2026-10-30T12:00:00+00:00"}
}}
POLICY = {"source": "approval-policy-demo-01", "max_age_seconds": 60,
          "allowed_reviewers": ["demo-owner"], "scope": "Static fixture allowlist is not real identity authentication."}


def instant(value):
    if not isinstance(value, str): raise ValueError("Timestamp text required")
    result = datetime.fromisoformat(value)
    if result.tzinfo is None or result.utcoffset() is None: raise ValueError("Timezone required")
    return result.astimezone(timezone.utc)


def assess(evidence, as_of):
    request, approval = evidence["request"], evidence["approval"]
    reference = instant(as_of)
    observed = [instant(item["observed_at"]) for item in (request, approval)]
    start, end = instant(approval["approved_at"]), instant(approval["expires_at"])
    if end <= start or start > observed[1] or any(t > reference for t in observed):
        raise ValueError("Invalid or future evidence timeline")
    if any(type(v) is not int or v < 1 for v in (request["revision"], approval["request_revision"])):
        raise ValueError("Positive integer revisions required")
    if any(type(approval[key]) is not bool for key in ("revoked", "consumed")):
        raise ValueError("Boolean lifecycle flags required")
    if approval["decision"] not in {"approve", "reject"}: raise ValueError("Invalid decision")
    reasons = []
    if any((reference-t).total_seconds() > POLICY["max_age_seconds"] for t in observed): reasons.append("stale_evidence")
    if request["request_id"] != approval["request_id"]: reasons.append("request_mismatch")
    if request["revision"] != approval["request_revision"]: reasons.append("revision_mismatch")
    if request["action"] != approval["action"] or request["scope"] != approval["scope"]: reasons.append("scope_or_action_mismatch")
    if approval["reviewer"] not in POLICY["allowed_reviewers"]: reasons.append("reviewer_not_allowed")
    if approval["decision"] != "approve": reasons.append("not_approved")
    if reference >= end: reasons.append("approval_expired")
    if approval["revoked"]: reasons.append("approval_revoked")
    if approval["consumed"]: reasons.append("approval_already_consumed")
    return {"source": "approval-assessment-demo-01", "inputs": [request["source"], approval["source"], POLICY["source"]],
            "status": "blocked_requires_fresh_review" if reasons else "eligible_snapshot_requires_execution_gate",
            "blocking_reasons": reasons, "expires_at": approval["expires_at"],
            "identity_authenticated": False, "execution_authorized": False, "actions_executed": False}


def tools():
    descriptions = {"lookup_request": "Read synthetic access request identity, revision and scope",
                    "lookup_approval": "Read recorded approval lifecycle metadata, not an execution token",
                    "assess_approval": "Check expiry, identity, revision, scope, reviewer and lifecycle; never grant access"}
    return [{"type": "function", "function": {"name": name, "description": description,
             "parameters": {"type": "object", "properties": {"request_id": {"type": "string"}},
                            "required": ["request_id"], "additionalProperties": False}}}
            for name, description in descriptions.items()]


def execute(name, arguments, request_id, as_of):
    if (name not in {t["function"]["name"] for t in tools()} or not isinstance(arguments, dict)
            or set(arguments) != {"request_id"} or arguments["request_id"] != request_id):
        raise ValueError("Invalid tool or request scope")
    evidence = REQUESTS.get(request_id)
    if evidence is None: raise ValueError("Unknown synthetic request")
    if name == "lookup_request": return [evidence["request"]]
    if name == "lookup_approval": return [evidence["approval"], POLICY]
    return [assess(evidence, as_of)]


def chat(messages):
    payload = {"model": os.environ.get("OLLAMA_MODEL", "qwen3:4b"), "messages": messages,
               "tools": tools(), "stream": False, "think": True,
               "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 2500}}
    request = urllib.request.Request("http://127.0.0.1:11434/api/chat",
                                    data=json.dumps(payload).encode(),
                                    headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)["message"]
