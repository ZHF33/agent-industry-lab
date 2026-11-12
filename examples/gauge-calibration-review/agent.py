"""Read-only review of synthetic dimensional calibration evidence."""
import json
import os
import urllib.request
from datetime import datetime, timezone

POLICY = {"source": "gauge-policy-demo-01", "gauge_id": "GAUGE-DEMO-A",
          "unit": "um", "limit": 5, "points": {"P10": 10000, "P20": 20000, "P30": 30000, "P40": 40000}}
READINGS = {"source": "gauge-readings-demo-01", "gauge_id": "GAUGE-DEMO-A",
            "captured_at": "2026-11-12T13:00:00Z", "unit": "um", "points": [
    {"point": "P10", "measured": 10003, "uncertainty": 2},
    {"point": "P20", "measured": 20004, "uncertainty": 2},
    {"point": "P30", "measured": 29993, "uncertainty": 1},
]}


def instant(value):
    if not isinstance(value, str):
        raise ValueError("Timestamp text required")
    parsed = datetime.fromisoformat(value)
    if parsed.utcoffset() is None:
        raise ValueError("Explicit offset required")
    return parsed.astimezone(timezone.utc)


def assess(policy, readings, as_of):
    if policy["gauge_id"] != readings["gauge_id"] or policy["unit"] != "um" or readings["unit"] != "um":
        raise ValueError("Gauge or unit mismatch")
    if instant(readings["captured_at"]) > instant(as_of):
        raise ValueError("Future reading snapshot")

    limit = policy["limit"]
    expected = policy["points"]
    records = readings["points"]
    if type(limit) is not int or limit < 0:
        raise ValueError("Expected a nonnegative integer limit")
    if not isinstance(expected, dict) or not 1 <= len(expected) <= 100:
        raise ValueError("Expected 1 to 100 reference points")
    if not isinstance(records, list) or len(records) > 100:
        raise ValueError("Expected up to 100 readings")
    by_point = {}
    for record in records:
        if not isinstance(record, dict) or set(record) != {"point", "measured", "uncertainty"}:
            raise ValueError("Invalid reading fields")
        point, measured, uncertainty = record["point"], record["measured"], record["uncertainty"]
        if not isinstance(point, str) or point not in expected or point in by_point:
            raise ValueError("Unknown or duplicate point")
        if type(measured) is not int or type(uncertainty) is not int or uncertainty < 0:
            raise ValueError("Expected integer reading and nonnegative uncertainty")
        by_point[point] = record

    results = []
    for point, reference in expected.items():
        if type(reference) is not int:
            raise ValueError("Expected integer reference")
        record = by_point.get(point)
        if record is None:
            results.append({"point": point, "reference": reference, "status": "missing_reading"})
            continue
        error = record["measured"] - reference
        uncertainty = record["uncertainty"]
        low, high = error - uncertainty, error + uncertainty
        if low >= -limit and high <= limit:
            status = "inside"
        elif low > limit or high < -limit:
            status = "outside"
        else:
            status = "overlaps_limit"
        results.append({**record, "reference": reference, "error": error,
                        "interval": [low, high], "status": status})
    return {"source": "calibration-assessment-demo-01",
            "inputs": [policy["source"], readings["source"]],
            "unit": "um", "tolerance": [-limit, limit], "points": results}


def tools():
    descriptions = {"lookup_policy": "Read synthetic gauge points, unit and tolerance",
                    "lookup_readings": "Read synthetic readings and uncertainty",
                    "assess_points": "Classify error intervals and missing points"}
    return [{"type": "function", "function": {"name": name, "description": description,
             "parameters": {"type": "object", "properties": {"gauge_id": {"type": "string"}},
                            "required": ["gauge_id"], "additionalProperties": False}}}
            for name, description in descriptions.items()]


def execute(name, arguments, gauge_id, as_of):
    if (name not in {"lookup_policy", "lookup_readings", "assess_points"}
            or arguments != {"gauge_id": gauge_id} or gauge_id != POLICY["gauge_id"]):
        raise ValueError("Invalid tool or gauge scope")
    if name == "lookup_policy":
        return [POLICY]
    if name == "lookup_readings":
        return [READINGS]
    return [assess(POLICY, READINGS, as_of)]


def chat(messages):
    payload = {"model": os.environ.get("OLLAMA_MODEL", "qwen3:4b"), "messages": messages,
               "tools": tools(), "stream": False, "think": True,
               "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 2500}}
    request = urllib.request.Request("http://127.0.0.1:11434/api/chat", data=json.dumps(payload).encode(),
                                    headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)["message"]
