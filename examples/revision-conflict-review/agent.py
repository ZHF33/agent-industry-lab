"""Read-only synthetic work-order revision review; no business writes."""
import json
import os
import urllib.request
from datetime import datetime, timezone

CHANGES = {"CHANGE-DEMO-01": {
    "proposal": {"source": "workorder-proposal-demo-01", "record_id": "WORK-DEMO-01", "base_revision": 4,
                 "observed_at": "2026-10-28T12:00:00+00:00", "patch": {"priority": "high"}},
    "record": {"source": "workorder-snapshot-demo-01", "record_id": "WORK-DEMO-01", "revision": 5,
               "observed_at": "2026-10-28T12:00:00+00:00", "status": "open", "priority": "low"}
}}
POLICY = {"source": "revision-review-policy-demo-01", "max_age_seconds": 60,
          "scope": "Proposal review only; actual write requires atomic version precondition and authorization."}


def instant(value):
    if not isinstance(value, str): raise ValueError("Timestamp text required")
    result = datetime.fromisoformat(value)
    if result.tzinfo is None or result.utcoffset() is None: raise ValueError("Timezone required")
    return result.astimezone(timezone.utc)


def assess(evidence, as_of):
    proposal, record = evidence["proposal"], evidence["record"]
    reference = instant(as_of)
    observed = [instant(item["observed_at"]) for item in (proposal, record)]
    if any(value > reference for value in observed): raise ValueError("Future evidence")
    revision, base = record["revision"], proposal["base_revision"]
    if type(revision) is not int or revision < 1 or (base is not None and (type(base) is not int or base < 1)):
        raise ValueError("Positive integer revisions required")
    patch = proposal["patch"]
    if not isinstance(patch, dict) or set(patch) != {"priority"} or patch["priority"] not in {"low", "normal", "high"}:
        raise ValueError("Only a priority patch is allowed")
    if record["status"] not in {"open", "closed"} or record["priority"] not in {"low", "normal", "high"}:
        raise ValueError("Invalid record state")
    identity = proposal["record_id"] == record["record_id"]
    fresh = all((reference-value).total_seconds() <= POLICY["max_age_seconds"] for value in observed)
    if not identity or not fresh:
        status = "insufficient_evidence"
    elif base is None:
        status = "missing_base_revision"
    elif base != revision:
        status = "revision_conflict"
    elif record["status"] == "closed":
        status = "closed_record_requires_review"
    else:
        status = "matching_snapshot_requires_review"
    return {"source": "revision-assessment-demo-01", "inputs": [proposal["source"], record["source"], POLICY["source"]],
            "identity_match": identity, "evidence_fresh": fresh, "status": status,
            "base_revision": base, "observed_revision": revision,
            "proposal_patch": patch, "current_priority": record["priority"],
            "write_authorized": False, "atomic_write_verified": False, "actions_executed": False}


def tools():
    descriptions = {"lookup_change": "Read synthetic proposed priority change and its base revision",
                    "lookup_record": "Read synthetic current work-order snapshot and revision",
                    "assess_revision": "Compare identity, freshness, base revision and record state; never update the record"}
    return [{"type": "function", "function": {"name": name, "description": description,
             "parameters": {"type": "object", "properties": {"change_id": {"type": "string"}},
                            "required": ["change_id"], "additionalProperties": False}}}
            for name, description in descriptions.items()]


def execute(name, arguments, change_id, as_of):
    if (name not in {t["function"]["name"] for t in tools()} or not isinstance(arguments, dict)
            or set(arguments) != {"change_id"} or arguments["change_id"] != change_id):
        raise ValueError("Invalid tool or change scope")
    evidence = CHANGES.get(change_id)
    if evidence is None: raise ValueError("Unknown synthetic change")
    if name == "lookup_change": return [evidence["proposal"]]
    if name == "lookup_record": return [evidence["record"], POLICY]
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
