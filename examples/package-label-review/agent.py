"""Review synthetic packaging label scans against a fixed job plan."""
import json
import os
import re
import urllib.request
from datetime import datetime, timezone

PLAN = {"source": "plan-demo-01", "job_id": "JOB-DEMO-A", "entries": {
    "BOX-A": "00123", "BOX-B": "00124", "BOX-C": "00125", "BOX-D": "00126",
}}
SCANS = {"source": "scan-demo-01", "job_id": "JOB-DEMO-A",
         "captured_at": "2026-11-10T14:00:00Z", "entries": {
    "BOX-A": "001236", "BOX-B": "001240", "BOX-C": "001236",
}}


def instant(value):
    if not isinstance(value, str):
        raise ValueError("Timestamp text required")
    parsed = datetime.fromisoformat(value)
    if parsed.utcoffset() is None:
        raise ValueError("Explicit offset required")
    return parsed.astimezone(timezone.utc)


def check_digit(payload):
    """Internal classroom rule for exactly five ASCII digits."""
    if not isinstance(payload, str) or re.fullmatch(r"[0-9]{5}", payload) is None:
        raise ValueError("Expected five ASCII digits")
    total = sum(int(digit) * weight for digit, weight in zip(payload, (3, 1, 3, 1, 3)))
    return str((-total) % 10)


def assess(plan, scans, as_of):
    if plan["job_id"] != scans["job_id"]:
        raise ValueError("Job identity mismatch")
    if instant(scans["captured_at"]) > instant(as_of):
        raise ValueError("Scan snapshot is later than review time")
    expected = plan["entries"]
    observed = scans["entries"]
    if not 1 <= len(expected) <= 100 or len(observed) > 100:
        raise ValueError("Invalid evidence size")
    if observed.keys() - expected.keys():
        raise ValueError("Scanned box outside job scope")
    rows = []
    for box, payload in sorted(expected.items()):
        intended = payload + check_digit(payload)
        scan = observed.get(box)
        if box not in observed:
            status = "missing_scan"
        elif not isinstance(scan, str) or re.fullmatch(r"[0-9]{6}", scan) is None:
            status = "invalid_format"
        elif check_digit(scan[:-1]) != scan[-1]:
            status = "invalid_check_digit"
        elif scan != intended:
            status = "wrong_code"
        else:
            status = "match"
        rows.append({"box": box, "expected": intended, "observed": scan, "status": status})
    return {"source": "label-assessment-demo-01", "inputs": [plan["source"], scans["source"]],
            "boxes": rows, "release_authorized": False}


def tools():
    descriptions = {"lookup_plan": "Read scoped job plan and expected label payloads",
                    "lookup_scans": "Read synthetic scanned labels with snapshot time",
                    "assess_labels": "Compare label format, check digit and job identity"}
    return [{"type": "function", "function": {"name": name, "description": description,
             "parameters": {"type": "object", "properties": {"job_id": {"type": "string"}},
                            "required": ["job_id"], "additionalProperties": False}}}
            for name, description in descriptions.items()]


def execute(name, arguments, job_id, as_of):
    if (name not in {"lookup_plan", "lookup_scans", "assess_labels"}
            or arguments != {"job_id": job_id} or job_id != PLAN["job_id"]):
        raise ValueError("Invalid tool or job scope")
    if name == "lookup_plan":
        return [PLAN]
    if name == "lookup_scans":
        return [SCANS]
    return [assess(PLAN, SCANS, as_of)]


def chat(messages):
    payload = {"model": os.environ.get("OLLAMA_MODEL", "qwen3:4b"), "messages": messages,
               "tools": tools(), "stream": False, "think": True,
               "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 2500}}
    request = urllib.request.Request("http://127.0.0.1:11434/api/chat", data=json.dumps(payload).encode(),
                                    headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)["message"]
