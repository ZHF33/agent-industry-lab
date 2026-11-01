"""Synthetic industrial-material telemetry review; no release or equipment control."""
import json
import os
import re
import urllib.request
from datetime import datetime, timezone
from fractions import Fraction

SHIPMENTS = {"SHIP-DEMO-01": {
    "shipment": {"source": "shipment-demo-01", "shipment_id": "SHIP-DEMO-01",
                 "material": "DEMO-INDUSTRIAL-MATERIAL", "window_start": "2026-11-01T12:00:00+00:00",
                 "window_end": "2026-11-01T12:20:00+00:00", "observed_at": "2026-11-01T12:20:00+00:00"},
    "readings": {"source": "readings-demo-01", "shipment_id": "SHIP-DEMO-01",
                 "observed_at": "2026-11-01T12:20:00+00:00", "samples": [
                     {"at": "2026-11-01T12:00:00+00:00", "value": "4", "unit": "C"},
                     {"at": "2026-11-01T12:05:00+00:00", "value": "50", "unit": "F"},
                     {"at": "2026-11-01T12:10:00+00:00", "value": "10", "unit": "C"},
                     {"at": "2026-11-01T12:20:00+00:00", "value": "4", "unit": "C"}]}
}}
POLICY = {"source": "thermal-policy-demo-01", "lower_c": "2", "upper_c": "8",
          "max_gap_seconds": 300, "max_age_seconds": 60,
          "scope": "Synthetic process limits, not product safety or release standards."}


def instant(value):
    if not isinstance(value, str): raise ValueError("Timestamp text required")
    result = datetime.fromisoformat(value)
    if result.tzinfo is None or result.utcoffset() is None or result.microsecond:
        raise ValueError("Whole-second timezone-aware timestamp required")
    return result.astimezone(timezone.utc)


def celsius(value, unit):
    if not isinstance(value, str) or not re.fullmatch(r"-?\d{1,5}(?:\.\d{1,6})?", value):
        raise ValueError("Bounded decimal text required")
    number = Fraction(value)
    if unit == "F": number = (number - 32) * Fraction(5, 9)
    elif unit != "C": raise ValueError("Supported units: C, F")
    if number < Fraction(-27315, 100): raise ValueError("Below absolute zero")
    return number


def assess(evidence, as_of):
    shipment, readings = evidence["shipment"], evidence["readings"]
    if shipment["shipment_id"] != readings["shipment_id"]: raise ValueError("Shipment mismatch")
    start, end, reference = map(instant, (shipment["window_start"], shipment["window_end"], as_of))
    observed = [instant(x["observed_at"]) for x in (shipment, readings)]
    if start >= end or end > reference or any(t > reference or t < end for t in observed):
        raise ValueError("Invalid or future observation window")
    raw = readings["samples"]
    if not isinstance(raw, list) or not 2 <= len(raw) <= 1000: raise ValueError("Need 2–1000 samples")
    rows = [(instant(r["at"]), celsius(r["value"], r["unit"])) for r in raw]
    if any(not start <= t <= end for t, _ in rows): raise ValueError("Sample outside window")
    if any(b[0] <= a[0] for a, b in zip(rows, rows[1:])): raise ValueError("Strict time order required")
    low, high = celsius(POLICY["lower_c"], "C"), celsius(POLICY["upper_c"], "C")
    above = below = within = 0
    unknown = int((rows[0][0]-start).total_seconds() + (end-rows[-1][0]).total_seconds())
    intervals = []
    for (left, value), (right, _) in zip(rows, rows[1:]):
        seconds = int((right-left).total_seconds())
        category = "unknown" if seconds > POLICY["max_gap_seconds"] else (
            "above" if value > high else "below" if value < low else "within")
        if category == "unknown": unknown += seconds
        elif category == "above": above += seconds
        elif category == "below": below += seconds
        else: within += seconds
        intervals.append({"from": left.isoformat(), "to": right.isoformat(), "seconds": seconds,
                          "held_value_category": category})
    points = [{"at": t.isoformat(), "celsius_exact": str(v)} for t, v in rows if v < low or v > high]
    reasons = []
    if any((reference-t).total_seconds() > POLICY["max_age_seconds"] for t in observed): reasons.append("stale_snapshot")
    if points: reasons.append("out_of_band_samples")
    if unknown: reasons.append("incomplete_time_coverage")
    return {"source": "excursion-assessment-demo-01", "inputs": [shipment["source"], readings["source"], POLICY["source"]],
            "status": "manual_exception_review" if reasons else "manual_receipt_review",
            "reasons": reasons, "sampled_peak_c_exact": str(max(v for _, v in rows)),
            "out_of_band_points": points, "estimated_above_seconds": above, "estimated_below_seconds": below,
            "estimated_within_seconds": within, "unknown_seconds": unknown, "intervals": intervals,
            "estimator": "Left sample held over short intervals only; not measured continuous exposure.",
            "release_authorized": False, "actions_executed": False}


def tools():
    descriptions = {"lookup_shipment": "Read scoped synthetic shipment window and process policy",
                    "lookup_readings": "Read scoped temperature samples with units and timestamps",
                    "assess_excursion": "Normalize units, list abnormal sampled points, estimate short intervals and unknown gaps"}
    return [{"type": "function", "function": {"name": name, "description": description,
             "parameters": {"type": "object", "properties": {"shipment_id": {"type": "string"}},
                            "required": ["shipment_id"], "additionalProperties": False}}}
            for name, description in descriptions.items()]


def execute(name, arguments, shipment_id, as_of):
    if (name not in {t["function"]["name"] for t in tools()} or not isinstance(arguments, dict)
            or set(arguments) != {"shipment_id"} or arguments["shipment_id"] != shipment_id):
        raise ValueError("Invalid tool or shipment scope")
    evidence = SHIPMENTS.get(shipment_id)
    if evidence is None: raise ValueError("Unknown synthetic shipment")
    if name == "lookup_shipment": return [evidence["shipment"], POLICY]
    if name == "lookup_readings": return [evidence["readings"]]
    return [assess(evidence, as_of)]


def chat(messages):
    payload = {"model": os.environ.get("OLLAMA_MODEL", "qwen3:4b"), "messages": messages,
               "tools": tools(), "stream": False, "think": True,
               "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 2500}}
    request = urllib.request.Request("http://127.0.0.1:11434/api/chat", data=json.dumps(payload).encode(),
                                    headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)["message"]
