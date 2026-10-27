"""Read-only token-bucket projection from synthetic snapshots; no API requests."""
import json
import os
import urllib.request
from datetime import datetime, timezone
from fractions import Fraction

SERVICES = {"SERVICE-DEMO-01": {
    "traffic": {"source": "traffic-demo-01", "service_id": "SERVICE-DEMO-01", "limit_version": "limit-v1",
                "observed_at": "2026-10-27T12:00:00+00:00", "tokens_at_observation": 3, "batch_requests": 11},
    "limit": {"source": "limit-demo-01", "service_id": "SERVICE-DEMO-01", "version": "limit-v1",
              "observed_at": "2026-10-27T12:00:00+00:00", "capacity": 10, "refill_per_second": "2"}
}}
POLICY = {"source": "quota-review-policy-demo-01", "max_age_seconds": 60,
          "assumption": "No intervening consumption; one token per request; atomic batch; no live admission."}


def instant(value):
    if not isinstance(value, str): raise ValueError("Timestamp text required")
    result = datetime.fromisoformat(value)
    if result.tzinfo is None or result.utcoffset() is None: raise ValueError("Timezone required")
    return result.astimezone(timezone.utc)


def project(capacity, tokens, refill, elapsed, demand):
    if any(type(x) is not int for x in (capacity, tokens, demand)) or capacity <= 0 or tokens < 0 or tokens > capacity or demand <= 0:
        raise ValueError("Invalid capacity, tokens or batch demand")
    if not isinstance(refill, str): raise ValueError("Refill must be rational text")
    try: rate = Fraction(refill)
    except (ValueError, ZeroDivisionError) as error: raise ValueError("Invalid refill rate") from error
    if rate < 0 or elapsed < 0: raise ValueError("Negative rate or elapsed time")
    available = min(Fraction(capacity), Fraction(tokens) + rate * elapsed)
    if demand > capacity:
        outcome, wait = "batch_exceeds_capacity", None
    elif available >= demand:
        outcome, wait = "projected_budget_sufficient", Fraction(0)
    elif rate == 0:
        outcome, wait = "no_refill_and_insufficient", None
    else:
        outcome, wait = "projected_budget_insufficient", (demand - available) / rate
    return {"projected_tokens": str(available), "projection_outcome": outcome,
            "ideal_wait_seconds": str(wait) if wait is not None else None}


def assess(record, as_of):
    traffic, limit = record["traffic"], record["limit"]
    reference = instant(as_of)
    observed = [instant(x["observed_at"]) for x in (traffic, limit)]
    if any(t > reference for t in observed): raise ValueError("Future evidence")
    fresh = all((reference-t).total_seconds() <= POLICY["max_age_seconds"] for t in observed)
    identity = traffic["service_id"] == limit["service_id"]
    version_match = traffic["limit_version"] == limit["version"]
    delta = reference - observed[0]
    # Exact elapsed microseconds; avoid float rounding in a boundary calculation.
    elapsed = Fraction((delta.days*86400 + delta.seconds)*1000000 + delta.microseconds, 1000000)
    result = project(limit["capacity"], traffic["tokens_at_observation"], limit["refill_per_second"], elapsed, traffic["batch_requests"])
    if not (fresh and identity and version_match):
        result = {"projected_tokens": None, "projection_outcome": "insufficient_evidence", "ideal_wait_seconds": None}
    return {"source": "quota-assessment-demo-01", "inputs": [traffic["source"], limit["source"], POLICY["source"]],
            "evidence_fresh": fresh, "identity_match": identity, "limit_version_match": version_match,
            **result, "live_admission": "unknown", "retry_executed": False, "actions_executed": False}


def tools():
    descriptions = {"lookup_traffic": "Read synthetic observed tokens and proposed atomic batch demand",
                    "lookup_limit": "Read synthetic capacity/refill configuration and version",
                    "assess_budget": "Compare scope, version and freshness; compute ideal no-consumption projection, never send requests"}
    return [{"type": "function", "function": {"name": name, "description": description,
             "parameters": {"type": "object", "properties": {"service_id": {"type": "string"}},
                            "required": ["service_id"], "additionalProperties": False}}}
            for name, description in descriptions.items()]


def execute(name, arguments, service_id, as_of):
    if (name not in {t["function"]["name"] for t in tools()} or not isinstance(arguments, dict)
            or set(arguments) != {"service_id"} or arguments["service_id"] != service_id):
        raise ValueError("Invalid tool or service scope")
    record = SERVICES.get(service_id)
    if record is None: raise ValueError("Unknown synthetic service")
    if name == "lookup_traffic": return [record["traffic"]]
    if name == "lookup_limit": return [record["limit"], POLICY]
    return [assess(record, as_of)]


def chat(messages):
    payload = {"model": os.environ.get("OLLAMA_MODEL", "qwen3:4b"), "messages": messages,
               "tools": tools(), "stream": False, "think": True,
               "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 2500}}
    request = urllib.request.Request("http://127.0.0.1:11434/api/chat",
                                    data=json.dumps(payload).encode(),
                                    headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)["message"]
