"""Replay synthetic pressure hysteresis; no live alarm or equipment writes."""
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

POLICY = {
    "source": "pressure-policy-demo-01",
    "system_id": "AIR-DEMO-A",
    "issued_at": "2026-11-24T12:30:50Z",
    "unit": "kPa",
    "low_below": 600,
    "recover_at_or_above": 650,
    "initial_state": "normal",
    "initial_state_at": "2026-11-24T12:30:50Z",
    "max_gap_seconds": 30,
}
READINGS_PATH = Path(__file__).with_name("readings.json")

def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def load_snapshot():
    return json.loads(READINGS_PATH.read_text(encoding="utf-8"), object_pairs_hook=unique_object)


def instant(value):
    if not isinstance(value, str):
        raise ValueError("Timestamp text required")
    parsed = datetime.fromisoformat(value)
    if parsed.utcoffset() is None:
        raise ValueError("Explicit offset required")
    return parsed.astimezone(timezone.utc)


def validate_scope(snapshot, policy, system_id, as_of):
    cutoff = instant(as_of)
    for evidence in (snapshot, policy):
        if evidence["system_id"] != system_id or instant(evidence["issued_at"]) > cutoff:
            raise ValueError("Evidence is out of scope or newer than review time")


def bounded_integer(value, maximum):
    if type(value) is not int or not 0 <= value <= maximum:
        raise ValueError("Expected bounded nonnegative integer")
    return value


def next_state(previous, pressure, low, recovery):
    if pressure < low:
        return "low"
    if pressure >= recovery:
        return "normal"
    return previous


def assess(snapshot, policy, as_of):
    validate_scope(snapshot, policy, policy["system_id"], as_of)
    cutoff = instant(as_of)
    low = bounded_integer(policy["low_below"], 2000)
    recovery = bounded_integer(policy["recover_at_or_above"], 2000)
    gap_limit = bounded_integer(policy["max_gap_seconds"], 3600)
    if low >= recovery or gap_limit == 0 or policy["unit"] != "kPa" or snapshot["unit"] != "kPa":
        raise ValueError("Invalid threshold, gap or unit contract")
    state = policy["initial_state"]
    if state not in {"normal", "low", "unknown"}:
        raise ValueError("Invalid initial state")
    previous_at = instant(policy["initial_state_at"])
    issued_at = instant(snapshot["issued_at"])
    if not previous_at <= instant(policy["issued_at"]) <= issued_at <= cutoff:
        raise ValueError("Invalid initial-state or evidence chronology")
    readings = snapshot["readings"]
    if not isinstance(readings, list) or not 1 <= len(readings) <= 1000:
        raise ValueError("Expected 1 to 1000 pressure readings")
    trace, entries, recoveries, resets = [], 0, 0, 0
    for position, row in enumerate(readings, 1):
        if not isinstance(row, dict) or set(row) != {"at", "pressure_kpa"}:
            raise ValueError("Invalid reading fields")
        at = instant(row["at"])
        if not previous_at < at <= issued_at:
            raise ValueError("Readings must have unique increasing times within evidence issuance")
        pressure = bounded_integer(row["pressure_kpa"], 2000)
        gap_seconds = (at - previous_at).total_seconds()
        reset = gap_seconds > gap_limit
        before = state
        if reset:
            state = "unknown"
            resets += 1
        after_gap = state
        state = next_state(state, pressure, low, recovery)
        # Recovery means low -> normal only; unknown -> normal merely establishes state.
        entries += int(after_gap != "low" and state == "low")
        recoveries += int(after_gap == "low" and state == "normal")
        trace.append({"row": position, "at": row["at"], "pressure_kpa": pressure,
                      "before": before, "gap_seconds": gap_seconds, "gap_reset": reset,
                      "after_gap": after_gap, "state": state})
        previous_at = at
    age = (cutoff - previous_at).total_seconds()
    return {"source": "pressure-replay-demo-01", "inputs": [snapshot["source"], policy["source"]],
            "system_id": policy["system_id"], "unit": "kPa",
            "low_entries": entries, "low_to_normal_recoveries": recoveries, "gap_resets": resets,
            "last_observed_state": state, "state_at_review": "unknown" if age > gap_limit else state,
            "last_reading_age_seconds": age, "trace": trace,
            "equipment_actions_executed": False}


TOOL_DESCRIPTIONS = {
    "lookup_policy": "Read low/recovery thresholds, explicit initial state and maximum accepted sampling gap",
    "lookup_readings": "Read the fixed synthetic pressure history in acquisition order",
    "replay_pressure": "Replay hysteresis, reset state after gaps and report stale review-time state",
}

def tools():
    return [{"type": "function", "function": {"name": name, "description": description,
             "parameters": {"type": "object", "properties": {"system_id": {"type": "string"}},
                            "required": ["system_id"], "additionalProperties": False}}}
            for name, description in TOOL_DESCRIPTIONS.items()]


def execute(name, arguments, system_id, as_of, snapshot):
    if name not in TOOL_DESCRIPTIONS or arguments != {"system_id": system_id}:
        raise ValueError("Invalid tool or system argument")
    validate_scope(snapshot, POLICY, system_id, as_of)
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
