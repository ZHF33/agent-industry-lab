"""Estimate pallet counts for isolated dispatch groups using synthetic evidence."""
import json
import os
import urllib.request
from datetime import datetime, timezone


PLAN = {
    "source": "dispatch-plan-demo-01",
    "dispatch_id": "DISPATCH-DEMO-A",
    "issued_at": "2026-11-16T13:00:00Z",
    "cartons_by_group": {"A": 9, "B": 7, "C": 4},
}
POLICY = {
    "source": "pallet-policy-demo-01",
    "dispatch_id": "DISPATCH-DEMO-A",
    "issued_at": "2026-11-16T12:30:00Z",
    "capacity_by_group": {"A": 8, "B": 8},
}


def instant(value):
    if not isinstance(value, str):
        raise ValueError("Timestamp text required")
    parsed = datetime.fromisoformat(value)
    if parsed.utcoffset() is None:
        raise ValueError("Explicit offset required")
    return parsed.astimezone(timezone.utc)


def carton_count(value):
    if type(value) is not int or not 0 <= value <= 1_000_000:
        raise ValueError("Expected a bounded nonnegative integer carton count")
    return value


def validate_scope(plan, policy, dispatch_id, as_of):
    cutoff = instant(as_of)
    for evidence in (plan, policy):
        if evidence["dispatch_id"] != dispatch_id or instant(evidence["issued_at"]) > cutoff:
            raise ValueError("Evidence is out of scope or newer than the review time")


def assess(plan, policy, as_of):
    validate_scope(plan, policy, plan["dispatch_id"], as_of)
    demand = plan["cartons_by_group"]
    capacities = policy["capacity_by_group"]
    if not 1 <= len(demand) <= 100 or capacities.keys() - demand.keys():
        raise ValueError("Invalid dispatch group scope")
    for capacity in capacities.values():
        if carton_count(capacity) == 0:
            raise ValueError("Pallet capacity must be positive")

    groups = []
    for group, raw_count in demand.items():
        cartons = carton_count(raw_count)
        capacity = capacities.get(group)
        row = {"group": group, "cartons": cartons, "capacity": capacity}
        if not cartons:
            row.update(status="no_demand", pallets=0)
        elif capacity is None:
            row.update(status="missing_capacity", pallets=None)
        else:
            full, remainder = divmod(cartons, capacity)
            row.update(status="estimated", pallets=full + int(remainder > 0),
                       full_pallets=full, remaining_cartons=remainder)
        groups.append(row)
    estimate_complete = all(row["pallets"] is not None for row in groups)
    subtotal = sum(row["pallets"] for row in groups if row["pallets"] is not None)
    return {"source": "pallet-assessment-demo-01", "inputs": [plan["source"], policy["source"]],
            "dispatch_id": plan["dispatch_id"], "groups": groups,
            "known_group_subtotal": subtotal,
            "total_pallets": subtotal if estimate_complete else None,
            "status": "estimated" if estimate_complete else "missing_capacity"}


TOOL_DESCRIPTIONS = {
    "lookup_policy": "Read approved carton capacity per pallet for each dispatch group",
    "lookup_plan": "Read carton demand by dispatch group",
    "assess_pallets": "Calculate whole pallet counts for separated groups and flag missing capacities",
}


def tools():
    return [{"type": "function", "function": {"name": name, "description": description,
             "parameters": {"type": "object", "properties": {"dispatch_id": {"type": "string"}},
                            "required": ["dispatch_id"], "additionalProperties": False}}}
            for name, description in TOOL_DESCRIPTIONS.items()]


def execute(name, arguments, dispatch_id, as_of):
    if name not in TOOL_DESCRIPTIONS or arguments != {"dispatch_id": dispatch_id}:
        raise ValueError("Invalid tool or dispatch argument")
    validate_scope(PLAN, POLICY, dispatch_id, as_of)
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
