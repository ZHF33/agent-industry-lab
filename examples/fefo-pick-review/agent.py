"""Propose first-expiry-first-out picks from one synthetic stock snapshot."""
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


POLICY = {
    "source": "pick-policy-demo-01",
    "request_id": "PICK-DEMO-A",
    "issued_at": "2026-11-21T12:30:00Z",
    "sku": "PART-DEMO-1",
    "demand": 9,
    "use_at": "2026-11-23T00:00:00Z",
}
STOCK_PATH = Path(__file__).with_name("lots.json")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def load_snapshot():
    return json.loads(STOCK_PATH.read_text(encoding="utf-8"), object_pairs_hook=unique_object)


def instant(value):
    if not isinstance(value, str):
        raise ValueError("Timestamp text required")
    parsed = datetime.fromisoformat(value)
    if parsed.utcoffset() is None:
        raise ValueError("Explicit offset required")
    return parsed.astimezone(timezone.utc)


def validate_scope(snapshot, policy, request_id, as_of):
    cutoff = instant(as_of)
    for evidence in (snapshot, policy):
        if evidence["request_id"] != request_id or instant(evidence["issued_at"]) > cutoff:
            raise ValueError("Evidence is out of scope or newer than review time")
    if snapshot["sku"] != policy["sku"] or instant(policy["use_at"]) < cutoff:
        raise ValueError("SKU mismatch or use time precedes review")


def assess(snapshot, policy, as_of):
    validate_scope(snapshot, policy, policy["request_id"], as_of)
    demand = policy["demand"]
    if type(demand) is not int or not 0 <= demand <= 1_000_000:
        raise ValueError("Invalid integer demand")
    lots = snapshot["lots"]
    if not isinstance(lots, list) or len(lots) > 100:
        raise ValueError("Expected a bounded lot list")

    use_at = instant(policy["use_at"])
    eligible, excluded, seen = [], [], set()
    for lot in lots:
        identity, available = lot["lot_id"], lot["available"]
        if not isinstance(identity, str) or not identity.strip() or identity in seen:
            raise ValueError("Missing or duplicate lot ID")
        seen.add(identity)
        if type(available) is not int or not 0 <= available <= 1_000_000 or type(lot["released"]) is not bool:
            raise ValueError("Invalid available quantity or quality release")
        expiry = instant(lot["expires_at"])
        reasons = []
        if not lot["released"]:
            reasons.append("quality_hold")
        if expiry <= use_at:
            reasons.append("expires_by_use")
        if reasons:
            excluded.append({"lot_id": identity, "reasons": reasons})
        else:
            eligible.append((expiry, identity, available))

    remaining, picks = demand, []
    for expiry, identity, available in sorted(eligible):
        quantity = min(available, remaining)
        if quantity:
            picks.append({"lot_id": identity, "quantity": quantity, "expires_at": expiry.isoformat()})
        remaining -= quantity
    return {"source": "pick-assessment-demo-01", "inputs": [snapshot["source"], policy["source"]],
            "request_id": policy["request_id"], "sku": policy["sku"],
            "demand": demand, "use_at": policy["use_at"], "picks": picks, "excluded": excluded,
            "allocated": demand - remaining, "shortage": remaining,
            "status": "short" if remaining else "proposed"}


TOOL_DESCRIPTIONS = {
    "lookup_policy": "Read SKU, demand and intended use time",
    "lookup_lots": "Read the fixed stock snapshot including lot expiry and quality release",
    "plan_pick": "Propose earliest-expiry picks from eligible lots and report shortage",
}


def tools():
    return [{"type": "function", "function": {"name": name, "description": description,
             "parameters": {"type": "object", "properties": {"request_id": {"type": "string"}},
                            "required": ["request_id"], "additionalProperties": False}}}
            for name, description in TOOL_DESCRIPTIONS.items()]


def execute(name, arguments, request_id, as_of, snapshot):
    if name not in TOOL_DESCRIPTIONS or arguments != {"request_id": request_id}:
        raise ValueError("Invalid tool or request argument")
    validate_scope(snapshot, POLICY, request_id, as_of)
    if name == "lookup_policy":
        return [POLICY]
    if name == "lookup_lots":
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
