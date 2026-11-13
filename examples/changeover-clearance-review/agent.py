"""Review synthetic clearance evidence after a station changeover."""
import json
import os
import urllib.request
from datetime import datetime, timezone

POLICY = {
    "source": "clearance-policy-demo-01", "station_id": "STATION-DEMO-A",
    "started_at": "2026-11-13T13:00:00Z",
    "checkpoints": ["table", "feeder", "bin", "rack"],
}
EVENTS = {
    "source": "clearance-events-demo-01", "station_id": "STATION-DEMO-A",
    "events": [
        {"id": "E01", "point": "table", "at": "2026-11-13T13:00:00Z", "state": "residue"},
        {"id": "E02", "point": "table", "at": "2026-11-13T13:07:00Z", "state": "clear"},
        {"id": "E03", "point": "feeder", "at": "2026-11-13T13:05:00Z", "state": "residue"},
        {"id": "E04", "point": "bin", "at": "2026-11-13T12:59:59Z", "state": "clear"},
        {"id": "E05", "point": "rack", "at": "2026-11-13T13:10:00Z", "state": "clear"},
        {"id": "E06", "point": "rack", "at": "2026-11-13T08:10:00-05:00", "state": "residue"},
        {"id": "E07", "point": "feeder", "at": "2026-11-13T13:11:00Z", "state": "clear"},
    ],
}


def instant(value):
    if not isinstance(value, str):
        raise ValueError("Timestamp text required")
    parsed = datetime.fromisoformat(value)
    if parsed.utcoffset() is None:
        raise ValueError("Explicit offset required")
    return parsed.astimezone(timezone.utc)


def assess(policy, snapshot, as_of):
    if policy["station_id"] != snapshot["station_id"]:
        raise ValueError("Station mismatch")
    start, end = instant(policy["started_at"]), instant(as_of)
    if end < start:
        raise ValueError("Review precedes changeover start")
    checkpoints, events = policy["checkpoints"], snapshot["events"]
    if (not isinstance(checkpoints, list) or not 1 <= len(checkpoints) <= 100
            or any(not isinstance(point, str) or not point.strip() for point in checkpoints)
            or len(set(checkpoints)) != len(checkpoints)):
        raise ValueError("Expected unique checkpoint IDs")
    if not isinstance(events, list) or len(events) > 200:
        raise ValueError("Expected up to 200 events")

    current = {point: [] for point in checkpoints}
    seen, excluded = set(), []
    for event in events:
        if not isinstance(event, dict) or set(event) != {"id", "point", "at", "state"}:
            raise ValueError("Invalid event fields")
        event_id, point = event["id"], event["point"]
        if not isinstance(event_id, str) or not event_id.strip() or event_id in seen:
            raise ValueError("Invalid or duplicate event ID")
        seen.add(event_id)
        if not isinstance(point, str) or point not in current or event["state"] not in ("clear", "residue"):
            raise ValueError("Invalid checkpoint or state")
        at = instant(event["at"])
        if not start <= at <= end:
            excluded.append(event_id)
            continue
        current[point].append((at, event))

    rows = []
    for point, candidates in current.items():
        if not candidates:
            rows.append({"point": point, "state": "missing_evidence", "event_ids": []})
            continue
        newest = max(at for at, _ in candidates)
        matches = [event for at, event in candidates if at == newest]
        states = sorted({event["state"] for event in matches})
        rows.append({"point": point, "at_utc": newest.isoformat(),
                     "state": states[0] if len(states) == 1 else "conflict",
                     "event_ids": sorted(event["id"] for event in matches)})
    return {"source": "clearance-assessment-demo-01", "inputs": [policy["source"], snapshot["source"]],
            "started_at": start.isoformat(), "as_of": end.isoformat(),
            "checkpoints": rows, "excluded_event_ids": sorted(excluded)}


def tools():
    descriptions = {"lookup_policy": "Read required checkpoints and changeover start",
                    "lookup_events": "Read checkpoint events with timestamps",
                    "assess_clearance": "Resolve latest evidence per checkpoint"}
    return [{"type": "function", "function": {"name": name, "description": description,
             "parameters": {"type": "object", "properties": {"station_id": {"type": "string"}},
                            "required": ["station_id"], "additionalProperties": False}}}
            for name, description in descriptions.items()]


def execute(name, arguments, station_id, as_of):
    if (name not in {"lookup_policy", "lookup_events", "assess_clearance"}
            or arguments != {"station_id": station_id} or station_id != POLICY["station_id"]):
        raise ValueError("Invalid tool or station scope")
    if name == "lookup_policy":
        return [POLICY]
    if name == "lookup_events":
        return [EVENTS]
    return [assess(POLICY, EVENTS, as_of)]


def chat(messages):
    payload = {"model": os.environ.get("OLLAMA_MODEL", "qwen3:4b"), "messages": messages,
               "tools": tools(), "stream": False, "think": True,
               "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 2500}}
    request = urllib.request.Request("http://127.0.0.1:11434/api/chat", data=json.dumps(payload).encode(),
                                    headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)["message"]
