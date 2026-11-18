"""Review a synthetic meter snapshot against a fixed tariff schedule."""
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


POLICY = {
    "source": "energy-policy-demo-01",
    "meter_id": "METER-DEMO-A",
    "issued_at": "2026-11-18T12:30:00Z",
    "cents_per_kwh": {"peak": 21, "off_peak": 11},
}
METER_PATH = Path(__file__).with_name("meter-snapshot.json")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def load_snapshot():
    return json.loads(METER_PATH.read_text(encoding="utf-8"), object_pairs_hook=unique_object)


def instant(value):
    if not isinstance(value, str):
        raise ValueError("Timestamp text required")
    parsed = datetime.fromisoformat(value)
    if parsed.utcoffset() is None:
        raise ValueError("Explicit offset required")
    return parsed.astimezone(timezone.utc)


def validate_scope(snapshot, policy, meter_id, as_of):
    cutoff = instant(as_of)
    for evidence in (snapshot, policy):
        if evidence["meter_id"] != meter_id or instant(evidence["issued_at"]) > cutoff:
            raise ValueError("Evidence is out of scope or newer than the review time")


def assess(snapshot, policy, as_of):
    validate_scope(snapshot, policy, policy["meter_id"], as_of)
    readings = snapshot["wh_by_slot"]
    rates = policy["cents_per_kwh"]
    if not rates or len(rates) > 24 or readings.keys() - rates.keys():
        raise ValueError("Invalid tariff-slot scope")
    rows = []
    known_millicents = 0
    missing = []
    for slot, rate in rates.items():
        if type(rate) is not int or not 0 <= rate <= 10_000:
            raise ValueError("Rate must be a bounded nonnegative integer")
        if slot not in readings:
            missing.append(slot)
            continue
        wh = readings[slot]
        if type(wh) is not int or not 0 <= wh <= 1_000_000_000:
            raise ValueError("Wh must be a bounded nonnegative integer")
        millicents = wh * rate
        known_millicents += millicents
        rows.append({"slot": slot, "wh": wh, "cents_per_kwh": rate, "millicents": millicents})

    total_cents = None if missing else (known_millicents + 500) // 1000
    return {"source": "energy-assessment-demo-01", "inputs": [snapshot["source"], policy["source"]],
            "meter_id": policy["meter_id"], "rows": rows, "missing_slots": missing,
            "known_millicents": known_millicents, "total_cents": total_cents,
            "status": "incomplete" if missing else "estimated"}


TOOL_DESCRIPTIONS = {
    "lookup_policy": "Read the synthetic tariff policy with one rate in cents/kWh per billing slot",
    "lookup_readings": "Read the captured meter readings in Wh by billing slot",
    "assess_charge": "Compute a synthetic usage charge and flag missing billing slots",
}


def tools():
    return [{"type": "function", "function": {"name": name, "description": description,
             "parameters": {"type": "object", "properties": {"meter_id": {"type": "string"}},
                            "required": ["meter_id"], "additionalProperties": False}}}
            for name, description in TOOL_DESCRIPTIONS.items()]


def execute(name, arguments, meter_id, as_of, snapshot):
    if name not in TOOL_DESCRIPTIONS or arguments != {"meter_id": meter_id}:
        raise ValueError("Invalid tool or meter argument")
    validate_scope(snapshot, POLICY, meter_id, as_of)
    if name == "lookup_policy":
        return [POLICY]
    if name == "lookup_readings":
        return [snapshot]
    return [assess(snapshot, POLICY, as_of)]


def chat(messages):
    payload = {"model": os.environ.get("OLLAMA_MODEL", "qwen3:4b"), "messages": messages,
               "tools": tools(), "stream": False, "think": True,
               "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 2500}}
    request = urllib.request.Request("http://127.0.0.1:11434/api/chat", data=json.dumps(payload).encode(),
                                    headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)["message"]
