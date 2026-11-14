"""Review synthetic per-tool machining counters and batch demand."""
import json
import os
import urllib.request
from datetime import datetime, timezone

POLICY = {
    "source": "tool-policy-demo-01", "machine_id": "MACHINE-DEMO-A",
    "tools": {
        "T1": {"limit": 100, "planned": 10},
        "T2": {"limit": 100, "planned": 11},
        "T3": {"limit": 100, "planned": 4},
        "T4": {"limit": 100, "planned": 5},
    },
}
COUNTERS = {
    "source": "tool-counters-demo-01", "machine_id": "MACHINE-DEMO-A",
    "previous_at": "2026-11-14T12:00:00Z", "current_at": "2026-11-14T13:00:00Z",
    "previous": {"T1": 80, "T2": 80, "T3": 88, "T4": 20},
    "current": {"T1": 90, "T2": 90, "T3": 5},
}


def instant(value):
    if not isinstance(value, str):
        raise ValueError("Timestamp text required")
    parsed = datetime.fromisoformat(value)
    if parsed.utcoffset() is None:
        raise ValueError("Explicit offset required")
    return parsed.astimezone(timezone.utc)


def cycles(value):
    if type(value) is not int or not 0 <= value <= 1_000_000_000:
        raise ValueError("Expected a bounded nonnegative integer cycle count")
    return value


def assess(policy, counters, as_of):
    if policy["machine_id"] != counters["machine_id"]:
        raise ValueError("Machine mismatch")
    previous_at = instant(counters["previous_at"])
    current_at = instant(counters["current_at"])
    if not previous_at < current_at <= instant(as_of):
        raise ValueError("Counter snapshots are out of order or in the future")

    specs = policy["tools"]
    previous, current = counters["previous"], counters["current"]
    if not 1 <= len(specs) <= 100 or (previous.keys() | current.keys()) - specs.keys():
        raise ValueError("Invalid tool scope")
    for counts in (previous, current):
        for value in counts.values():
            cycles(value)

    rows = []
    for tool_id, spec in specs.items():
        limit, planned = cycles(spec["limit"]), cycles(spec["planned"])
        if limit == 0:
            raise ValueError("Tool life limit must be positive")
        before, after = previous.get(tool_id), current.get(tool_id)
        row = {"tool_id": tool_id, "limit": limit, "planned": planned,
               "previous": before, "current": after}
        if before is None or after is None:
            row["status"] = "missing_counter"
        elif after < before:
            row["status"] = "counter_regression"
        else:
            projected = after + planned
            row["projected"] = projected
            row["status"] = "fits_limit" if projected <= limit else "exceeds_limit"
        rows.append(row)
    return {"source": "life-assessment-demo-01", "inputs": [policy["source"], counters["source"]],
            "previous_at": previous_at.isoformat(), "current_at": current_at.isoformat(),
            "tools": rows}


def tools():
    descriptions = {"lookup_policy": "Read tool life limits and planned cycles",
                    "lookup_counters": "Read the previous and current cumulative counts",
                    "assess_life": "Check continuity and project next batch usage"}
    return [{"type": "function", "function": {"name": name, "description": description,
             "parameters": {"type": "object", "properties": {"machine_id": {"type": "string"}},
                            "required": ["machine_id"], "additionalProperties": False}}}
            for name, description in descriptions.items()]


def execute(name, arguments, machine_id, as_of):
    if (name not in {"lookup_policy", "lookup_counters", "assess_life"}
            or arguments != {"machine_id": machine_id} or machine_id != POLICY["machine_id"]):
        raise ValueError("Invalid tool or machine scope")
    if name == "lookup_policy":
        return [POLICY]
    if name == "lookup_counters":
        return [COUNTERS]
    return [assess(POLICY, COUNTERS, as_of)]


def chat(messages):
    payload = {"model": os.environ.get("OLLAMA_MODEL", "qwen3:4b"), "messages": messages,
               "tools": tools(), "stream": False, "think": True,
               "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 2500}}
    request = urllib.request.Request("http://127.0.0.1:11434/api/chat", data=json.dumps(payload).encode(),
                                    headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)["message"]
