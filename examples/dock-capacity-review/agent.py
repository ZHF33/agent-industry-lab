"""Review simultaneous reservations for a pool of interchangeable loading docks."""
import json
import os
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone


PLAN = {
    "source": "dock-bookings-demo-01",
    "pool_id": "POOL-DEMO-A",
    "issued_at": "2026-11-17T12:45:00Z",
    "bookings": [
        {"booking_id": "A", "start": "2026-11-18T09:00:00Z", "end": "2026-11-18T10:00:00Z"},
        {"booking_id": "B", "start": "2026-11-18T09:15:00Z", "end": "2026-11-18T10:15:00Z"},
        {"booking_id": "C", "start": "2026-11-18T04:30:00-05:00", "end": "2026-11-18T05:00:00-05:00"},
        {"booking_id": "D", "start": "2026-11-18T10:00:00Z", "end": "2026-11-18T10:30:00Z"},
    ],
}
POLICY = {
    "source": "dock-capacity-demo-01",
    "pool_id": "POOL-DEMO-A",
    "issued_at": "2026-11-17T12:30:00Z",
    "capacity": 2,
}


def instant(value):
    if not isinstance(value, str):
        raise ValueError("Timestamp text required")
    parsed = datetime.fromisoformat(value)
    if parsed.utcoffset() is None:
        raise ValueError("Explicit offset required")
    return parsed.astimezone(timezone.utc)


def validate_scope(plan, policy, pool_id, as_of):
    cutoff = instant(as_of)
    for evidence in (plan, policy):
        if evidence["pool_id"] != pool_id or instant(evidence["issued_at"]) > cutoff:
            raise ValueError("Evidence is out of scope or newer than the review time")


def assess(plan, policy, as_of):
    validate_scope(plan, policy, plan["pool_id"], as_of)
    capacity = policy["capacity"]
    if type(capacity) is not int or not 0 <= capacity <= 100:
        raise ValueError("Invalid dock capacity")
    bookings = plan["bookings"]
    if len(bookings) > 100:
        raise ValueError("Too many bookings for one review")

    starts, ends = defaultdict(set), defaultdict(set)
    seen = set()
    for booking in bookings:
        identity = booking["booking_id"]
        if not isinstance(identity, str) or not identity.strip() or identity in seen:
            raise ValueError("Missing or duplicate booking ID")
        seen.add(identity)
        start, end = instant(booking["start"]), instant(booking["end"])
        if end <= start:
            raise ValueError("Booking end must follow start")
        starts[start].add(identity)
        ends[end].add(identity)

    boundaries = sorted(starts.keys() | ends.keys())
    peak, conflicts, active = 0, [], set()
    for start, end in zip(boundaries, boundaries[1:]):
        active.difference_update(ends[start])
        active.update(starts[start])
        count = len(active)
        peak = max(peak, count)
        if count > capacity:
            conflicts.append({"start": start.isoformat(), "end": end.isoformat(),
                              "booking_ids": sorted(active), "required": count,
                              "shortage": count - capacity})
    return {"source": "dock-assessment-demo-01", "inputs": [plan["source"], policy["source"]],
            "pool_id": plan["pool_id"], "capacity": capacity, "peak": peak,
            "conflicts": conflicts, "status": "capacity_conflict" if conflicts else "within_capacity"}


TOOL_DESCRIPTIONS = {
    "lookup_policy": "Read the constant capacity for the loading-dock pool",
    "lookup_plan": "Read appointment IDs and time ranges for the pool",
    "assess_docks": "Compare simultaneous reservations against dock capacity and list collision windows",
}


def tools():
    return [{"type": "function", "function": {"name": name, "description": description,
             "parameters": {"type": "object", "properties": {"pool_id": {"type": "string"}},
                            "required": ["pool_id"], "additionalProperties": False}}}
            for name, description in TOOL_DESCRIPTIONS.items()]


def execute(name, arguments, pool_id, as_of):
    if name not in TOOL_DESCRIPTIONS or arguments != {"pool_id": pool_id}:
        raise ValueError("Invalid tool or dock-pool argument")
    validate_scope(PLAN, POLICY, pool_id, as_of)
    if name == "lookup_policy":
        return [POLICY]
    if name == "lookup_plan":
        return [PLAN]
    return [assess(PLAN, POLICY, as_of)]


def chat(messages):
    payload = {"model": os.environ.get("OLLAMA_MODEL", "qwen3:4b"), "messages": messages,
               "tools": tools(), "stream": False, "think": True,
               "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 2500}}
    request = urllib.request.Request("http://127.0.0.1:11434/api/chat", data=json.dumps(payload).encode(),
                                    headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)["message"]
