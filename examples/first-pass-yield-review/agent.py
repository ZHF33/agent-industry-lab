"""Review synthetic first-pass inspection counts."""
import json
import os
import urllib.request
from datetime import datetime, timezone

POLICY = {
    "source": "fpy-policy-demo-01",
    "window_id": "WINDOW-DEMO-A",
    "minimum_bps": 9500,
    "lines": ("LINE-A", "LINE-B", "LINE-C"),
}
COUNTS = {
    "source": "fpy-counts-demo-01",
    "window_id": "WINDOW-DEMO-A",
    "closed_at": "2026-11-15T13:00:00Z",
    "rows": {
        "LINE-A": {"passed": 90, "inspected": 90},
        "LINE-B": {"passed": 5, "inspected": 10},
        "LINE-C": {"passed": 0, "inspected": 0},
    },
}


def instant(value):
    if not isinstance(value, str):
        raise ValueError("Timestamp text required")
    parsed = datetime.fromisoformat(value)
    if parsed.utcoffset() is None:
        raise ValueError("Explicit offset required")
    return parsed.astimezone(timezone.utc)


def count(value):
    if type(value) is not int or not 0 <= value <= 1_000_000_000:
        raise ValueError("Expected a bounded nonnegative integer count")
    return value


def assess(policy, counts, as_of):
    if policy["window_id"] != counts["window_id"] or instant(counts["closed_at"]) > instant(as_of):
        raise ValueError("Mismatched or future inspection window")
    lines, rows = policy["lines"], counts["rows"]
    minimum = count(policy["minimum_bps"])
    if minimum > 10_000 or not 1 <= len(lines) <= 100 or len(set(lines)) != len(lines):
        raise ValueError("Invalid reporting policy")
    if rows.keys() - set(lines):
        raise ValueError("Unexpected line")

    details = []
    for line in lines:
        if line not in rows:
            details.append({"line": line, "status": "missing"})
            continue
        passed, inspected = count(rows[line]["passed"]), count(rows[line]["inspected"])
        if passed > inspected:
            raise ValueError("Passed exceeds inspected")
        status = "observed" if inspected else "no_inspections"
        details.append({"line": line, "passed": passed, "inspected": inspected, "status": status})

    report = {"source": "fpy-assessment-demo-01", "inputs": [policy["source"], counts["source"]],
              "window_id": counts["window_id"], "closed_at": counts["closed_at"],
              "minimum_bps": minimum, "lines": details, "ratio": None}
    if any(row["status"] == "missing" for row in details):
        return {**report, "status": "missing_lines"}
    passed = sum(row["passed"] for row in details)
    inspected = sum(row["inspected"] for row in details)
    if not inspected:
        return {**report, "status": "no_inspections"}
    status = "meets_target" if passed * 10_000 >= minimum * inspected else "below_target"
    return {**report, "status": status, "ratio": {"passed": passed, "inspected": inspected}}


def tools():
    descriptions = {
        "lookup_policy": "Read expected lines and the minimum yield in basis points",
        "lookup_counts": "Read the closed window's first-pass counts by line",
        "assess_yield": "Check evidence coverage and compare pooled counts to the yield target",
    }
    return [{"type": "function", "function": {"name": name, "description": description,
             "parameters": {"type": "object", "properties": {"window_id": {"type": "string"}},
                            "required": ["window_id"], "additionalProperties": False}}}
            for name, description in descriptions.items()]


def execute(name, arguments, window_id, as_of):
    if (name not in {"lookup_policy", "lookup_counts", "assess_yield"}
            or arguments != {"window_id": window_id} or window_id != POLICY["window_id"]):
        raise ValueError("Invalid tool or window scope")
    if instant(COUNTS["closed_at"]) > instant(as_of):
        raise ValueError("Window not closed as of ticket")
    if name == "lookup_policy":
        return [POLICY]
    if name == "lookup_counts":
        return [COUNTS]
    return [assess(POLICY, COUNTS, as_of)]


def chat(messages):
    payload = {"model": os.environ.get("OLLAMA_MODEL", "qwen3:4b"), "messages": messages,
               "tools": tools(), "stream": False, "think": True,
               "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 2500}}
    request = urllib.request.Request("http://127.0.0.1:11434/api/chat", data=json.dumps(payload).encode(),
                                    headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)["message"]
