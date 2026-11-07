"""Reconcile synthetic equipment inspection records against a bounded checklist."""
import json
import os
import re
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone

CHECKLIST = {"source": "checklist-demo-01", "checklist_id": "CHECK-DEMO-A", "revision": 2,
             "entries": [{"device_id": "PUMP-A", "check_id": "SEAL"},
                         {"device_id": "PUMP-A", "check_id": "TEMP"},
                         {"device_id": "PUMP-B", "check_id": "TEMP"}]}
OBSERVATIONS = {"source": "observations-demo-01", "checklist_id": "CHECK-DEMO-A", "revision": 2,
                "observed_at": "2026-11-07T12:00:00Z", "entries": [
                    {"device_id": "PUMP-A", "check_id": "SEAL", "record_id": "R1", "result": "pass"},
                    {"device_id": "PUMP-A", "check_id": "SEAL", "record_id": "R2", "result": "fail"},
                    {"device_id": "PUMP-B", "check_id": "TEMP", "record_id": "R3", "result": "pass"},
                    {"device_id": "PUMP-C", "check_id": "TEMP", "record_id": "R4", "result": "pass"}]}
POLICY = {"source": "inspection-policy-demo-01", "max_rows_per_list": 100, "max_age_seconds": 60}


def instant(value):
    if not isinstance(value, str):
        raise ValueError("Timestamp text required")
    parsed = datetime.fromisoformat(value)
    if parsed.utcoffset() is None:
        raise ValueError("Explicit offset required")
    return parsed.astimezone(timezone.utc)


def identifier(value):
    return isinstance(value, str) and re.fullmatch(r"[A-Z0-9-]{1,64}", value) is not None


def key(row):
    pair = row["device_id"], row["check_id"]
    if not all(identifier(part) for part in pair):
        raise ValueError("Valid device and check IDs required")
    return pair


def reconcile(planned, observed):
    if any(not isinstance(rows, list) or len(rows) > POLICY["max_rows_per_list"]
           for rows in (planned, observed)):
        raise ValueError("At most 100 rows per list")
    expected = set()
    for row in planned:
        if not isinstance(row, dict) or set(row) != {"device_id", "check_id"}:
            raise ValueError("Invalid checklist fields")
        pair = key(row)
        if pair in expected:
            raise ValueError("Repeated checklist pair")
        expected.add(pair)

    groups = defaultdict(list)
    record_ids = set()
    for row in observed:
        if not isinstance(row, dict) or set(row) != {"device_id", "check_id", "record_id", "result"}:
            raise ValueError("Invalid observation fields")
        record_id = row["record_id"]
        if not identifier(record_id) or record_id in record_ids:
            raise ValueError("Unique record ID required")
        if row["result"] not in ("pass", "fail"):
            raise ValueError("Invalid inspection result")
        record_ids.add(record_id)
        groups[key(row)].append({"record_id": record_id, "result": row["result"]})

    def describe(pair):
        return {"device_id": pair[0], "check_id": pair[1],
                "records": sorted(groups.get(pair, []), key=lambda row: row["record_id"])}

    actual = set(groups)
    return {"planned_count": len(expected), "observed_record_count": len(record_ids),
            "matched_pair_count": len(expected & actual),
            "missing": [describe(pair) for pair in sorted(expected - actual)],
            "unexpected": [describe(pair) for pair in sorted(actual - expected)],
            "multiple": [describe(pair) for pair in sorted(actual) if len(groups[pair]) > 1],
            "conflicts": [describe(pair) for pair in sorted(actual)
                          if len({row["result"] for row in groups[pair]}) > 1],
            "failed_records": [describe(pair) for pair in sorted(actual)
                               if any(row["result"] == "fail" for row in groups[pair])]}


def assess(checklist, evidence, as_of):
    if checklist["checklist_id"] != evidence["checklist_id"]:
        raise ValueError("Checklist identity mismatch")
    for revision in (checklist["revision"], evidence["revision"]):
        if type(revision) is not int or revision < 1:
            raise ValueError("Positive integer revisions required")
    captured, reference = instant(evidence["observed_at"]), instant(as_of)
    if captured > reference:
        raise ValueError("Future evidence")
    limitations = []
    if checklist["revision"] != evidence["revision"]:
        limitations.append("revision_mismatch")
    if (reference - captured).total_seconds() > POLICY["max_age_seconds"]:
        limitations.append("stale_evidence")
    return {"source": "reconciliation-assessment-demo-01",
            **reconcile(checklist["entries"], evidence["entries"]), "limitations": limitations,
            "inputs": [checklist["source"], evidence["source"], POLICY["source"]],
            "release_authorized": False, "actions_executed": False}


def tools():
    descriptions = {"lookup_checklist": "Read scoped checklist revision and device/check pairs",
                    "lookup_observations": "Read synthetic inspection records and snapshot metadata",
                    "assess_reconciliation": "Compare pair membership, multiplicity, outcome conflicts and snapshot limits"}
    return [{"type": "function", "function": {"name": name, "description": description,
             "parameters": {"type": "object", "properties": {"checklist_id": {"type": "string"}},
                            "required": ["checklist_id"], "additionalProperties": False}}}
            for name, description in descriptions.items()]


def execute(name, arguments, checklist_id, as_of):
    if (name not in {"lookup_checklist", "lookup_observations", "assess_reconciliation"}
            or arguments != {"checklist_id": checklist_id} or checklist_id != CHECKLIST["checklist_id"]):
        raise ValueError("Invalid tool or checklist scope")
    if name == "lookup_checklist":
        return [CHECKLIST, POLICY]
    if name == "lookup_observations":
        return [OBSERVATIONS]
    return [assess(CHECKLIST, OBSERVATIONS, as_of)]


def chat(messages):
    payload = {"model": os.environ.get("OLLAMA_MODEL", "qwen3:4b"), "messages": messages,
               "tools": tools(), "stream": False, "think": True,
               "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 2500}}
    request = urllib.request.Request("http://127.0.0.1:11434/api/chat", data=json.dumps(payload).encode(),
                                    headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)["message"]
