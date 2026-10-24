"""Read-only synthetic product cache evidence; no Redis or business writes."""
import json
import os
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation


PRODUCTS = {"PRODUCT-DEMO-01": {
    "origin": {"source": "origin-product-demo-02", "product_id": "PRODUCT-DEMO-01",
               "version": "v2", "currency": "USD", "price": "9.00",
               "updated_at": "2026-10-24T11:00:00+00:00", "observed_at": "2026-10-24T11:05:00+00:00"},
    "cache": {"source": "cache-product-demo-01", "product_id": "PRODUCT-DEMO-01",
              "origin_version": "v1", "currency": "USD", "price": "8.50",
              "written_at": "2026-10-24T10:58:00+00:00", "observed_at": "2026-10-24T11:05:00+00:00",
              "ttl_seconds_at_observation": 180},
}}
POLICY = {"source": "cache-policy-demo-01", "max_snapshot_age_seconds": 60,
          "rule": "TTL describes key expiry, not authoritative data version. Never mutate cache from this review."}


def instant(value):
    if not isinstance(value, str):
        raise ValueError("Timestamp text required")
    result = datetime.fromisoformat(value)
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("Timezone required")
    return result.astimezone(timezone.utc)


def money(value):
    if not isinstance(value, str):
        raise ValueError("Price must be decimal text")
    try:
        amount = Decimal(value)
    except InvalidOperation as error:
        raise ValueError("Invalid price") from error
    if not amount.is_finite() or amount < 0 or amount.as_tuple().exponent < -2:
        raise ValueError("Non-negative finite price with at most 2 decimals required")
    return amount


def assess(record, as_of):
    origin, cache = record["origin"], record["cache"]
    reference = instant(as_of)
    observed_origin, observed_cache = instant(origin["observed_at"]), instant(cache["observed_at"])
    updated, written = instant(origin["updated_at"]), instant(cache["written_at"])
    if not updated <= observed_origin <= reference or not written <= observed_cache <= reference:
        raise ValueError("Invalid or future evidence timeline")
    ttl = cache["ttl_seconds_at_observation"]
    if type(ttl) is not int or ttl < -2:
        raise ValueError("Invalid Redis-style TTL observation")
    same_product = origin["product_id"] == cache["product_id"]
    fresh = all((reference - t).total_seconds() <= POLICY["max_snapshot_age_seconds"]
                for t in (observed_origin, observed_cache))
    age = (reference - observed_cache).total_seconds()
    if ttl == -2:
        state, remaining = "missing_at_observation", None
    elif ttl == -1:
        state, remaining = "no_expiry_at_observation", None
    else:
        remaining = max(0, ttl - age)
        state = "positive_ttl_projection" if remaining > 0 else "elapsed_ttl_projection"
    comparable = same_product and fresh and ttl != -2
    same_currency = origin["currency"] == cache["currency"]
    version_match = (origin["version"] == cache["origin_version"]) if comparable else None
    difference = str((money(cache["price"]) - money(origin["price"])).quantize(Decimal("0.01"))) if comparable and same_currency else None
    warnings = []
    if not same_product:
        warnings.append("product_identity_mismatch")
    if not fresh:
        warnings.append("stale_evidence")
    if comparable and not version_match:
        warnings.append("origin_version_mismatch")
    if comparable and not same_currency:
        warnings.append("currency_mismatch")
    if difference is not None and Decimal(difference) != 0:
        warnings.append("price_mismatch")
    if ttl == -1:
        warnings.append("no_expiry_recorded")
    return {"source": "cache-assessment-demo-01", "inputs": [origin["source"], cache["source"], POLICY["source"]],
            "as_of": reference.isoformat(), "evidence_fresh": fresh,
            "cache_state_from_snapshot": state, "projected_remaining_ttl_seconds": remaining,
            "origin_version_match": version_match, "cache_minus_origin_price": difference,
            "warnings": warnings, "current_cache_presence": "unknown",
            "checkout_price_verified": False, "invalidation_executed": False,
            "actions_executed": False}


def tools():
    descriptions = {"lookup_origin": "Read fixed authoritative synthetic product snapshot with source version",
                    "lookup_cache": "Read synthetic cache snapshot and TTL observation; no live Redis access",
                    "assess_consistency": "Compare identity, freshness, currency, price and origin version; project observed TTL without assuming live presence"}
    return [{"type": "function", "function": {"name": name, "description": description,
             "parameters": {"type": "object", "properties": {"product_id": {"type": "string"}},
                            "required": ["product_id"], "additionalProperties": False}}}
            for name, description in descriptions.items()]


def execute(name, arguments, product_id, as_of):
    if (name not in {t["function"]["name"] for t in tools()}
            or not isinstance(arguments, dict) or set(arguments) != {"product_id"}
            or arguments["product_id"] != product_id):
        raise ValueError("Invalid tool or product scope")
    record = PRODUCTS.get(product_id)
    if record is None:
        raise ValueError("Unknown synthetic product")
    if name == "lookup_origin":
        return [record["origin"]]
    if name == "lookup_cache":
        return [record["cache"], POLICY]
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
