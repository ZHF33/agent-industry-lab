"""Review assembly material sufficiency for one synthetic work order."""
import json
import os
import urllib.request
from datetime import datetime, timezone


PLAN = {
    "source": "kit-stock-demo-01",
    "order_id": "ORDER-DEMO-A",
    "issued_at": "2026-11-19T13:00:00Z",
    "available": {"BODY": 10, "BOLT": 19, "SEAL": 0},
}
POLICY = {
    "source": "kit-bom-demo-01",
    "order_id": "ORDER-DEMO-A",
    "issued_at": "2026-11-19T12:30:00Z",
    "bom_revision": "DEMO-R1",
    "target_units": 10,
    "per_unit": {"BODY": 1, "BOLT": 2, "SEAL": 1},
}


def instant(value):
    if not isinstance(value, str):
        raise ValueError("Timestamp text required")
    parsed = datetime.fromisoformat(value)
    if parsed.utcoffset() is None:
        raise ValueError("Explicit offset required")
    return parsed.astimezone(timezone.utc)


def quantity(value):
    if type(value) is not int or not 0 <= value <= 1_000_000:
        raise ValueError("Expected a bounded nonnegative integer piece count")
    return value


def validate_scope(stock, bom, order_id, as_of):
    cutoff = instant(as_of)
    for evidence in (stock, bom):
        if evidence["order_id"] != order_id or instant(evidence["issued_at"]) > cutoff:
            raise ValueError("Evidence is out of scope or newer than review time")


def assess(stock, bom, as_of):
    validate_scope(stock, bom, bom["order_id"], as_of)
    target = quantity(bom["target_units"])
    requirements = bom["per_unit"]
    available = stock["available"]
    if not 1 <= len(requirements) <= 100 or available.keys() - requirements.keys():
        raise ValueError("Invalid material scope")
    for value in available.values():
        quantity(value)

    rows = []
    missing = []
    for material, raw_required in requirements.items():
        per_unit = quantity(raw_required)
        if per_unit == 0:
            raise ValueError("BOM usage must be positive")
        needed = per_unit * target
        if material not in available:
            missing.append(material)
            rows.append({"material": material, "per_unit": per_unit, "needed": needed,
                         "available": None, "supported_units": None, "shortage": None})
            continue
        count = available[material]
        rows.append({"material": material, "per_unit": per_unit, "needed": needed,
                     "available": count, "supported_units": count // per_unit,
                     "shortage": max(needed - count, 0)})

    raw_capacity = None if missing else min(row["supported_units"] for row in rows)
    limiting = [] if missing else [row["material"] for row in rows if row["supported_units"] == raw_capacity]
    fulfillable = None if missing else min(target, raw_capacity)
    return {"source": "kit-assessment-demo-01", "inputs": [stock["source"], bom["source"]],
            "order_id": bom["order_id"], "bom_revision": bom["bom_revision"],
            "target_units": target, "materials": rows, "missing_materials": missing,
            "material_capacity": raw_capacity, "limiting_materials": limiting,
            "fulfillable_units": fulfillable,
            "status": "incomplete" if missing else "sufficient" if fulfillable == target else "short"}


TOOL_DESCRIPTIONS = {
    "lookup_bom": "Read the work-order quantity and per-unit bill of materials",
    "lookup_stock": "Read the dedicated available piece counts for this work order",
    "assess_kit": "Compute complete assembly units, limiting materials and target shortages",
}


def tools():
    return [{"type": "function", "function": {"name": name, "description": description,
             "parameters": {"type": "object", "properties": {"order_id": {"type": "string"}},
                            "required": ["order_id"], "additionalProperties": False}}}
            for name, description in TOOL_DESCRIPTIONS.items()]


def execute(name, arguments, order_id, as_of):
    if name not in TOOL_DESCRIPTIONS or arguments != {"order_id": order_id}:
        raise ValueError("Invalid tool or order argument")
    validate_scope(PLAN, POLICY, order_id, as_of)
    if name == "lookup_bom":
        return [POLICY]
    if name == "lookup_stock":
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
