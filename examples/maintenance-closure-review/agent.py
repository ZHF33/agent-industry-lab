"""Review required close-out evidence for one synthetic maintenance work order."""
import json
import os
import urllib.request
from datetime import datetime, timezone


PLAN = {
    "source": "closure-evidence-demo-01",
    "order_id": "MAINT-DEMO-A",
    "issued_at": "2026-11-20T13:00:00Z",
    "checks": {
        "repair_record": {"source": "repair-demo-01", "passed": True},
        "trial_record": {"source": "trial-demo-01", "passed": False},
    },
}
POLICY = {
    "source": "closure-policy-demo-01",
    "order_id": "MAINT-DEMO-A",
    "issued_at": "2026-11-20T12:30:00Z",
    "required": ["repair_record", "trial_record", "parts_return"],
}


def instant(value):
    if not isinstance(value, str):
        raise ValueError("Timestamp text required")
    parsed = datetime.fromisoformat(value)
    if parsed.utcoffset() is None:
        raise ValueError("Explicit offset required")
    return parsed.astimezone(timezone.utc)


def validate_scope(evidence, policy, order_id, as_of):
    cutoff = instant(as_of)
    for item in (evidence, policy):
        if item["order_id"] != order_id or instant(item["issued_at"]) > cutoff:
            raise ValueError("Evidence is out of scope or newer than review time")


def assess(evidence, policy, as_of):
    validate_scope(evidence, policy, policy["order_id"], as_of)
    required = policy["required"]
    checks = evidence["checks"]
    if (not isinstance(required, list) or not 1 <= len(required) <= 100
            or any(not isinstance(key, str) or not key.strip() for key in required)
            or len(set(required)) != len(required)):
        raise ValueError("A nonempty unique required-check list is needed")
    if checks.keys() - set(required):
        raise ValueError("Unexpected check outside the policy")

    rows, failed, missing = [], [], []
    for key in required:
        if key not in checks:
            missing.append(key)
            rows.append({"check": key, "status": "missing", "source": None})
            continue
        record = checks[key]
        if (not isinstance(record, dict) or type(record.get("passed")) is not bool
                or not isinstance(record.get("source"), str) or not record["source"].strip()):
            raise ValueError("A boolean result and source ID are required")
        status = "passed" if record["passed"] else "failed"
        if not record["passed"]:
            failed.append(key)
        rows.append({"check": key, "status": status, "source": record["source"]})

    verdict = "blocked" if failed else "needs_evidence" if missing else "ready_for_review"
    return {"source": "closure-assessment-demo-01",
            "inputs": [policy["source"], evidence["source"]],
            "order_id": policy["order_id"], "checks": rows,
            "failed_checks": failed, "missing_checks": missing, "verdict": verdict}


TOOL_DESCRIPTIONS = {
    "lookup_policy": "Read the work order's mandatory close-out evidence checklist",
    "lookup_evidence": "Read observed boolean evidence results and source IDs",
    "assess_closure": "List failures and missing checks and compute close-out review readiness",
}


def tools():
    return [{"type": "function", "function": {"name": name, "description": description,
             "parameters": {"type": "object", "properties": {"order_id": {"type": "string"}},
                            "required": ["order_id"], "additionalProperties": False}}}
            for name, description in TOOL_DESCRIPTIONS.items()]


def execute(name, arguments, order_id, as_of):
    if name not in TOOL_DESCRIPTIONS or arguments != {"order_id": order_id}:
        raise ValueError("Invalid tool or order argument")
    validate_scope(PLAN, POLICY, order_id, as_of)
    if name == "lookup_policy":
        return [POLICY]
    if name == "lookup_evidence":
        return [PLAN]
    return [assess(PLAN, POLICY, as_of)]


def chat(messages):
    payload = {"model": os.environ.get("OLLAMA_MODEL", "qwen3:4b"), "messages": messages,
               "tools": tools(), "stream": False, "think": True,
               "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 2500}}
    request = urllib.request.Request("http://127.0.0.1:11434/api/chat", data=json.dumps(payload).encode(),
                                    headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)["message"]
