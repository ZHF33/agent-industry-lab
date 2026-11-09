"""Read-only review of expiry evidence at planned arrival."""
import json
import os
import urllib.request
from datetime import datetime, timezone

SHIPMENT = {"source": "shipment-demo-01", "shipment_id": "SHIP-DEMO-A",
            "arrival_at": "2026-11-10T12:00:00Z", "min_remaining_hours": 24,
            "lot_ids": ["LOT-A", "LOT-B", "LOT-C", "LOT-D", "LOT-E"]}
LOTS = {"source": "lots-demo-01", "shipment_id": "SHIP-DEMO-A", "entries": [
    {"lot_id": "LOT-A", "expires_at": "2026-11-11T07:00:00-05:00"},
    {"lot_id": "LOT-B", "expires_at": "2026-11-11T11:59:59Z"},
    {"lot_id": "LOT-C", "expires_at": "2026-11-10T12:00:00Z"},
    {"lot_id": "LOT-D", "expires_at": None},
]}


def instant(value):
    if not isinstance(value, str):
        raise ValueError("Timestamp text required")
    parsed = datetime.fromisoformat(value)
    if parsed.utcoffset() is None:
        raise ValueError("Explicit offset required")
    return parsed.astimezone(timezone.utc)


def assess(shipment, lots, as_of):
    if shipment["shipment_id"] != lots["shipment_id"]:
        raise ValueError("Shipment identity mismatch")
    arrival = instant(shipment["arrival_at"])
    if arrival < instant(as_of):
        raise ValueError("Planned arrival precedes review time")
    hours = shipment["min_remaining_hours"]
    if type(hours) is not int or not 0 <= hours <= 8760:
        raise ValueError("Invalid minimum remaining hours")
    expected = shipment["lot_ids"]
    if (not isinstance(expected, list) or not 1 <= len(expected) <= 100
            or any(not isinstance(item, str) or not item.strip() for item in expected)
            or len(expected) != len(set(expected))):
        raise ValueError("Expected 1 to 100 unique lot IDs")
    entries = lots["entries"]
    if not isinstance(entries, list) or len(entries) > 100:
        raise ValueError("Invalid lot evidence size")
    observed = {}
    scope = set(expected)
    for row in entries:
        if not isinstance(row, dict) or set(row) != {"lot_id", "expires_at"}:
            raise ValueError("Invalid evidence fields")
        lot_id = row["lot_id"]
        if not isinstance(lot_id, str) or lot_id not in scope or lot_id in observed:
            raise ValueError("Unexpected or duplicate lot evidence")
        observed[lot_id] = row["expires_at"]

    report = []
    for lot_id in expected:
        expires_at = observed.get(lot_id)
        remaining = None if expires_at is None else (instant(expires_at) - arrival).total_seconds()
        if lot_id not in observed:
            status = "missing_lot"
        elif remaining is None:
            status = "missing_expiry"
        elif remaining <= 0:
            status = "expired_at_arrival"
        elif remaining < hours * 3600:
            status = "below_minimum"
        else:
            status = "meets_demo_threshold"
        report.append({"lot_id": lot_id, "status": status, "expires_at": expires_at,
                       "remaining_seconds": remaining})
    return {"source": "life-assessment-demo-01", "inputs": [shipment["source"], lots["source"]],
            "arrival_at": shipment["arrival_at"], "minimum_hours": hours, "lots": report,
            "dispatch_authorized": False}


def tools():
    descriptions = {"lookup_shipment": "Read shipment plan, expected lot IDs and minimum hours",
                    "lookup_lots": "Read synthetic expiry evidence",
                    "assess_life": "Compute remaining shelf life and exceptions at planned arrival"}
    return [{"type": "function", "function": {"name": name, "description": description,
             "parameters": {"type": "object", "properties": {"shipment_id": {"type": "string"}},
                            "required": ["shipment_id"], "additionalProperties": False}}}
            for name, description in descriptions.items()]


def execute(name, arguments, shipment_id, as_of):
    if (name not in {"lookup_shipment", "lookup_lots", "assess_life"}
            or arguments != {"shipment_id": shipment_id} or shipment_id != SHIPMENT["shipment_id"]):
        raise ValueError("Invalid tool or shipment scope")
    if name == "lookup_shipment":
        return [SHIPMENT]
    if name == "lookup_lots":
        return [LOTS]
    return [assess(SHIPMENT, LOTS, as_of)]


def chat(messages):
    payload = {"model": os.environ.get("OLLAMA_MODEL", "qwen3:4b"), "messages": messages,
               "tools": tools(), "stream": False, "think": True,
               "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 2500}}
    request = urllib.request.Request("http://127.0.0.1:11434/api/chat", data=json.dumps(payload).encode(),
                                    headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)["message"]
