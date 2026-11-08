"""Read-only spare issue quantity review with integer piece accounting."""
import json
import os
import re
import urllib.request
from datetime import datetime, timezone

REQUEST = {"source": "request-demo-01", "request_id": "REQ-DEMO-A", "revision": 1,
           "entries": [{"part_id": "BEARING-A", "quantity": 10, "unit": "piece"},
                       {"part_id": "SEAL-B", "quantity": 4, "unit": "piece"},
                       {"part_id": "FILTER-C", "quantity": 1, "unit": "piece"}]}
MOVEMENTS = {"source": "movements-demo-01", "request_id": "REQ-DEMO-A", "revision": 1,
             "observed_at": "2026-11-08T12:00:00Z", "entries": [
                 {"record_id": "M1", "part_id": "BEARING-A", "direction": "issue", "quantity": 8, "unit": "piece"},
                 {"record_id": "M2", "part_id": "BEARING-A", "direction": "return", "quantity": 1, "unit": "piece"},
                 {"record_id": "M3", "part_id": "SEAL-B", "direction": "issue", "quantity": 5, "unit": "piece"},
                 {"record_id": "M4", "part_id": "FILTER-C", "direction": "return", "quantity": 1, "unit": "piece"}]}
POLICY = {"source": "quantity-policy-demo-01", "max_rows": 100, "max_age_seconds": 60}


def instant(value):
    if not isinstance(value, str):
        raise ValueError("Timestamp text required")
    parsed = datetime.fromisoformat(value)
    if parsed.utcoffset() is None:
        raise ValueError("Explicit offset required")
    return parsed.astimezone(timezone.utc)


def identifier(value):
    return isinstance(value, str) and re.fullmatch(r"[A-Z0-9-]{1,64}", value) is not None


def quantity(row):
    if row["unit"] != "piece" or type(row["quantity"]) is not int or not 1 <= row["quantity"] <= 1000000:
        raise ValueError("Positive integer pieces, bounded to one million, required")
    if not identifier(row["part_id"]):
        raise ValueError("Invalid part ID")
    return row["quantity"]


def reconcile(planned, movements):
    if any(not isinstance(rows, list) or len(rows) > POLICY["max_rows"] for rows in (planned, movements)):
        raise ValueError("At most 100 rows per list")
    requested = {}
    for row in planned:
        if not isinstance(row, dict) or set(row) != {"part_id", "quantity", "unit"}:
            raise ValueError("Invalid request fields")
        value = quantity(row)
        if row["part_id"] in requested:
            raise ValueError("Duplicate requested part")
        requested[row["part_id"]] = value
    grouped, record_ids = {}, set()
    for row in movements:
        if not isinstance(row, dict) or set(row) != {"record_id", "part_id", "direction", "quantity", "unit"}:
            raise ValueError("Invalid movement fields")
        value = quantity(row)
        if not identifier(row["record_id"]) or row["record_id"] in record_ids:
            raise ValueError("Unique record ID required")
        if row["direction"] not in {"issue", "return"}:
            raise ValueError("Invalid direction")
        record_ids.add(row["record_id"])
        totals = grouped.setdefault(row["part_id"], {"issue": 0, "return": 0, "record_ids": []})
        totals[row["direction"]] += value
        totals["record_ids"].append(row["record_id"])
    result = []
    for part in sorted(set(requested) | set(grouped)):
        totals = grouped.get(part, {"issue": 0, "return": 0, "record_ids": []})
        expected = requested.get(part, 0)
        net = totals["issue"] - totals["return"]
        flags = []
        if part not in requested:
            flags.append("unrequested_part")
        if net < expected:
            flags.append("shortage")
        if net > expected:
            flags.append("excess")
        if totals["return"] > totals["issue"]:
            flags.append("return_exceeds_issue")
        result.append({"part_id": part, "unit": "piece", "requested": expected,
                       "issued": totals["issue"], "returned": totals["return"],
                       "net_issued": net, "difference": net - expected,
                       "record_ids": sorted(totals["record_ids"]), "flags": flags})
    return result


def assess(request, evidence, as_of):
    if request["request_id"] != evidence["request_id"]:
        raise ValueError("Request identity mismatch")
    for revision in (request["revision"], evidence["revision"]):
        if type(revision) is not int or revision < 1:
            raise ValueError("Positive integer revision required")
    observed, reference = instant(evidence["observed_at"]), instant(as_of)
    if observed > reference:
        raise ValueError("Future evidence")
    limitations = []
    if request["revision"] != evidence["revision"]:
        limitations.append("revision_mismatch")
    if (reference - observed).total_seconds() > POLICY["max_age_seconds"]:
        limitations.append("stale_evidence")
    return {"source": "balance-assessment-demo-01",
            "parts": reconcile(request["entries"], evidence["entries"]),
            "limitations": limitations,
            "inputs": [request["source"], evidence["source"], POLICY["source"]],
            "actions_executed": False, "stock_release_authorized": False}


def tools():
    descriptions = {"lookup_request": "Read scoped requested spare quantities and policy",
                    "lookup_movements": "Read scoped issue/return records with snapshot metadata",
                    "assess_balance": "Compute net issue, per-part differences and evidence limits"}
    return [{"type": "function", "function": {"name": name, "description": description,
             "parameters": {"type": "object", "properties": {"request_id": {"type": "string"}},
                            "required": ["request_id"], "additionalProperties": False}}}
            for name, description in descriptions.items()]


def execute(name, arguments, request_id, as_of):
    if (name not in {"lookup_request", "lookup_movements", "assess_balance"}
            or arguments != {"request_id": request_id} or request_id != REQUEST["request_id"]):
        raise ValueError("Invalid tool or request scope")
    if name == "lookup_request":
        return [REQUEST, POLICY]
    if name == "lookup_movements":
        return [MOVEMENTS]
    return [assess(REQUEST, MOVEMENTS, as_of)]


def chat(messages):
    payload = {"model": os.environ.get("OLLAMA_MODEL", "qwen3:4b"), "messages": messages,
               "tools": tools(), "stream": False, "think": True,
               "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 2500}}
    request = urllib.request.Request("http://127.0.0.1:11434/api/chat", data=json.dumps(payload).encode(),
                                    headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)["message"]
