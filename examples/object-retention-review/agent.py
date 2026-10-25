"""Synthetic metadata review. No storage connection or object mutation."""
import json
import os
import urllib.request
from datetime import datetime, timezone

OBJECTS = {"OBJECT-DEMO-01": {
    "inventory": {"source": "object-inventory-demo-01", "object_id": "OBJECT-DEMO-01",
                  "observed_at": "2026-10-25T12:00:00+00:00", "complete": True,
                  "versions": [{"version_id": "marker-v2", "kind": "delete_marker", "current": True},
                               {"version_id": "data-v1", "kind": "data", "current": False}]},
    "retention": {"source": "object-retention-demo-01", "object_id": "OBJECT-DEMO-01",
                  "observed_at": "2026-10-25T12:00:00+00:00",
                  "versions": [{"version_id": "data-v1", "retain_until": "2026-11-25T00:00:00+00:00", "legal_hold": False}]}
}}
POLICY = {"source": "retention-review-policy-demo-01", "max_age_seconds": 60,
          "scope": "Fixed retain-until metadata and legal hold only; no deletion authorization assessment."}


def instant(value):
    if not isinstance(value, str):
        raise ValueError("Timestamp text required")
    result = datetime.fromisoformat(value)
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("Timezone required")
    return result.astimezone(timezone.utc)


def assess(record, as_of):
    inventory, retention = record["inventory"], record["retention"]
    reference = instant(as_of)
    observed = [instant(x["observed_at"]) for x in (inventory, retention)]
    if any(t > reference for t in observed):
        raise ValueError("Future observation")
    if type(inventory["complete"]) is not bool:
        raise ValueError("Completeness must be boolean")
    versions, rows = inventory["versions"], retention["versions"]
    for entries in (versions, rows):
        ids = [x["version_id"] for x in entries]
        if any(not isinstance(x, str) or not x for x in ids) or len(set(ids)) != len(ids):
            raise ValueError("Missing or duplicate version identity")
    if any(x["kind"] not in {"data", "delete_marker"} or type(x["current"]) is not bool for x in versions):
        raise ValueError("Invalid version kind or current flag")
    current = [x for x in versions if x["current"]]
    if len(current) != 1:
        raise ValueError("Exactly one current version required in fixture")
    known_data = {x["version_id"] for x in versions if x["kind"] == "data"}
    if any(x["version_id"] not in known_data for x in rows):
        raise ValueError("Retention does not match known data version")
    fresh = all((reference-t).total_seconds() <= POLICY["max_age_seconds"] for t in observed)
    identity = inventory["object_id"] == retention["object_id"]
    usable = fresh and identity and inventory["complete"]
    findings = []
    by_id = {x["version_id"]: x for x in rows}
    for version_id in sorted(known_data):
        row = by_id.get(version_id)
        if row is None:
            findings.append({"version_id": version_id, "status": "missing_retention_evidence"})
            continue
        if type(row["legal_hold"]) is not bool:
            raise ValueError("Legal hold must be boolean")
        until = instant(row["retain_until"]) if row["retain_until"] is not None else None
        status = "insufficient_evidence"
        if usable:
            status = "restriction_recorded" if row["legal_hold"] or (until is not None and until > reference) else "no_active_restriction_recorded"
        findings.append({"version_id": version_id, "status": status,
                         "retain_until": row["retain_until"], "legal_hold": row["legal_hold"]})
    return {"source": "retention-assessment-demo-01", "inputs": [inventory["source"], retention["source"], POLICY["source"]],
            "evidence_fresh": fresh, "identity_match": identity, "inventory_complete": inventory["complete"],
            "current_kind_from_snapshot": current[0]["kind"] if usable else "unknown",
            "known_data_versions": len(known_data), "version_findings": findings,
            "object_readability": "unknown", "deletion_authorized": False, "actions_executed": False}


def tools():
    descriptions = {"lookup_object_versions": "Read synthetic version inventory including delete markers, not object bytes",
                    "lookup_retention": "Read version-specific synthetic fixed retention and legal hold metadata",
                    "assess_retention": "Assess identity, freshness, version coverage and recorded restrictions; never authorize deletion"}
    return [{"type": "function", "function": {"name": name, "description": description,
             "parameters": {"type": "object", "properties": {"object_id": {"type": "string"}},
                            "required": ["object_id"], "additionalProperties": False}}}
            for name, description in descriptions.items()]


def execute(name, arguments, object_id, as_of):
    if (name not in {t["function"]["name"] for t in tools()}
            or not isinstance(arguments, dict) or set(arguments) != {"object_id"}
            or arguments["object_id"] != object_id):
        raise ValueError("Invalid tool or object scope")
    record = OBJECTS.get(object_id)
    if record is None:
        raise ValueError("Unknown synthetic object")
    if name == "lookup_object_versions":
        return [record["inventory"]]
    if name == "lookup_retention":
        return [record["retention"], POLICY]
    return [assess(record, as_of)]


def chat(messages):
    payload = {"model": os.environ.get("OLLAMA_MODEL", "qwen3:4b"), "messages": messages,
               "tools": tools(), "stream": False, "think": True,
               "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 2500}}
    request = urllib.request.Request("http://127.0.0.1:11434/api/chat",
                                    data=json.dumps(payload).encode(),
                                    headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)["message"]
