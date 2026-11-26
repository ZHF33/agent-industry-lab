"""Bounded exhaustive cut selection for one synthetic stock bar; no machine writes."""
import itertools
import json
import os
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

POLICY = {
    "source": "cut-policy-demo-01",
    "stock_id": "BAR-DEMO-A",
    "issued_at": "2026-11-26T12:30:00Z",
    "material_id": "MAT-DEMO",
    "unit": "mm",
    "kerf_mm": 5,
    "max_age_seconds": 60,
    "objective": "length-then-cut-count-then-ids-v1",
}
STOCK_PATH = Path(__file__).with_name("stock_orders.json")

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


def validate_scope(snapshot, policy, stock_id, as_of):
    cutoff = instant(as_of)
    for evidence in (snapshot, policy):
        if evidence["stock_id"] != stock_id or instant(evidence["issued_at"]) > cutoff:
            raise ValueError("Evidence is out of scope or newer than review time")


def identifier(value):
    if not isinstance(value, str) or re.fullmatch(r"[A-Za-z0-9_-]{1,32}", value) is None:
        raise ValueError("Expected ASCII identifier up to 32 characters")
    return value


def positive_integer(value, maximum):
    if type(value) is not int or not 1 <= value <= maximum:
        raise ValueError("Expected bounded positive integer")
    return value


def assess(snapshot, policy, as_of):
    validate_scope(snapshot, policy, policy["stock_id"], as_of)
    age = (instant(as_of) - instant(snapshot["issued_at"])).total_seconds()
    limit = positive_integer(policy["max_age_seconds"], 3600)
    if age > limit or snapshot["declared_complete"] is not True:
        raise ValueError("Fresh complete stock/order snapshot required")
    if snapshot["unit"] != "mm" or policy["unit"] != "mm":
        raise ValueError("Integer millimetre contract required")
    if identifier(snapshot["material_id"]) != identifier(policy["material_id"]):
        raise ValueError("Stock material does not match the order contract")
    if policy["objective"] != "length-then-cut-count-then-ids-v1":
        raise ValueError("Unsupported objective")
    stock_length = positive_integer(snapshot["length_mm"], 10000)
    kerf = positive_integer(policy["kerf_mm"], 20)
    requests = snapshot["requests"]
    if not isinstance(requests, list) or not 1 <= len(requests) <= 10:
        raise ValueError("Expected 1 to 10 indivisible single-piece requests")
    pieces, seen = [], set()
    for row in requests:
        if not isinstance(row, dict) or set(row) != {"piece_id", "length_mm"}:
            raise ValueError("Invalid request fields")
        piece_id = identifier(row["piece_id"])
        if piece_id in seen:
            raise ValueError("Duplicate piece ID")
        seen.add(piece_id)
        pieces.append({"piece_id": piece_id, "length_mm": positive_integer(row["length_mm"], 10000)})
    pieces.sort(key=lambda row: row["piece_id"])
    best_key, selected = None, ()
    considered, feasible = 0, 0
    for count in range(len(pieces) + 1):
        for candidate in itertools.combinations(pieces, count):
            considered += 1
            delivered = sum(row["length_mm"] for row in candidate)
            if delivered + count * kerf > stock_length:
                continue
            feasible += 1
            key = (-delivered, count, tuple(row["piece_id"] for row in candidate))
            if best_key is None or key < best_key:
                best_key, selected = key, candidate
    delivered = sum(row["length_mm"] for row in selected)
    kerf_loss = len(selected) * kerf
    selected_ids = {row["piece_id"] for row in selected}
    return {"source": "cut-plan-demo-01", "inputs": [snapshot["source"], policy["source"]],
            "stock_id": policy["stock_id"], "material_id": policy["material_id"], "unit": "mm",
            "objective": policy["objective"], "selected": list(selected),
            "unselected_ids": sorted(seen - selected_ids), "delivered_mm": delivered,
            "kerf_loss_mm": kerf_loss, "used_mm": delivered + kerf_loss,
            "remainder_mm": stock_length - delivered - kerf_loss,
            "candidates_checked": considered, "feasible_candidates": feasible,
            "optimal_within_contract": True,
            "status": "proposal" if selected else "no_piece_fits",
            "saw_actions_executed": False}


TOOL_DESCRIPTIONS = {
    "lookup_policy": "Read kerf convention, material/unit contract, freshness and objective priorities",
    "lookup_stock_orders": "Read one fixed synthetic stock bar and bounded indivisible piece requests",
    "plan_cut": "Exhaustively compare at most 1024 subsets and propose maximum delivered length with explicit ties",
}

def tools():
    return [{"type": "function", "function": {"name": name, "description": description,
             "parameters": {"type": "object", "properties": {"stock_id": {"type": "string"}},
                            "required": ["stock_id"], "additionalProperties": False}}}
            for name, description in TOOL_DESCRIPTIONS.items()]


def execute(name, arguments, stock_id, as_of, snapshot):
    if name not in TOOL_DESCRIPTIONS or arguments != {"stock_id": stock_id}:
        raise ValueError("Invalid tool or stock argument")
    validate_scope(snapshot, POLICY, stock_id, as_of)
    if name == "lookup_policy":
        return [POLICY]
    if name == "lookup_stock_orders":
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
