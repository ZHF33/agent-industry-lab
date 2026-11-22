"""Review gaps and conflicting payloads in a bounded synthetic sequence window."""
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


POLICY = {
    "source": "sequence-policy-demo-01",
    "stream_id": "STREAM-DEMO-A",
    "issued_at": "2026-11-22T12:30:00Z",
    "first": 100,
    "last": 105,
}
EVENTS_PATH = Path(__file__).with_name("events.json")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def load_snapshot():
    return json.loads(EVENTS_PATH.read_text(encoding="utf-8"), object_pairs_hook=unique_object)


def instant(value):
    if not isinstance(value, str):
        raise ValueError("Timestamp text required")
    parsed = datetime.fromisoformat(value)
    if parsed.utcoffset() is None:
        raise ValueError("Explicit offset required")
    return parsed.astimezone(timezone.utc)


def validate_scope(snapshot, policy, stream_id, as_of):
    cutoff = instant(as_of)
    for evidence in (snapshot, policy):
        if evidence["stream_id"] != stream_id or instant(evidence["issued_at"]) > cutoff:
            raise ValueError("Evidence is out of scope or newer than review time")


def sequence_number(value):
    if type(value) is not int or not 0 <= value <= 1_000_000_000_000:
        raise ValueError("Expected a bounded nonnegative integer sequence number")
    return value


def assess(snapshot, policy, as_of):
    validate_scope(snapshot, policy, policy["stream_id"], as_of)
    first, last = sequence_number(policy["first"]), sequence_number(policy["last"])
    if first > last:
        raise ValueError("Expected first <= last")
    events = snapshot["events"]
    if not isinstance(events, list) or len(events) > 1000:
        raise ValueError("Expected at most 1000 event records")
    grouped = {}
    for position, event in enumerate(events, 1):
        if not isinstance(event, dict) or set(event) != {"sequence", "state"}:
            raise ValueError("Invalid event fields")
        number = sequence_number(event["sequence"])
        state = event["state"]
        if not first <= number <= last or not isinstance(state, str) or not state.strip() or len(state) > 100:
            raise ValueError("Invalid sequence scope or state")
        group = grouped.setdefault(number, {"states": set(), "positions": []})
        group["states"].add(state)
        group["positions"].append(position)

    missing_ranges, repeats, conflicts = [], [], []
    cursor = first
    for number, group in sorted(grouped.items()):
        if cursor < number:
            missing_ranges.append({"first": cursor, "last": number - 1})
        cursor = number + 1
        if len(group["positions"]) > 1:
            repeats.append({"sequence": number, "row_positions": group["positions"],
                            "states": sorted(group["states"])})
        if len(group["states"]) > 1:
            conflicts.append(number)
    if cursor <= last:
        missing_ranges.append({"first": cursor, "last": last})
    missing_count = sum(row["last"] - row["first"] + 1 for row in missing_ranges)
    return {"source": "sequence-assessment-demo-01", "inputs": [snapshot["source"], policy["source"]],
            "stream_id": policy["stream_id"], "expected_first": first, "expected_last": last,
            "record_count": len(events), "unique_count": len(grouped),
            "missing_ranges": missing_ranges, "missing_count": missing_count,
            "repeated_sequences": repeats, "conflicting_sequences": conflicts,
            "status": "conflicting" if conflicts else "incomplete" if missing_ranges else "covered"}


TOOL_DESCRIPTIONS = {
    "lookup_policy": "Read the independently declared inclusive sequence bounds",
    "lookup_events": "Read the fixed synthetic stream snapshot with sequence numbers and states",
    "assess_sequence": "Find missing ranges, repeats and conflicting states without enumerating missing numbers",
}


def tools():
    return [{"type": "function", "function": {"name": name, "description": description,
             "parameters": {"type": "object", "properties": {"stream_id": {"type": "string"}},
                            "required": ["stream_id"], "additionalProperties": False}}}
            for name, description in TOOL_DESCRIPTIONS.items()]


def execute(name, arguments, stream_id, as_of, snapshot):
    if name not in TOOL_DESCRIPTIONS or arguments != {"stream_id": stream_id}:
        raise ValueError("Invalid tool or stream argument")
    validate_scope(snapshot, POLICY, stream_id, as_of)
    if name == "lookup_policy":
        return [POLICY]
    if name == "lookup_events":
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
