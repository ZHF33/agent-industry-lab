"""Read-only certificate inventory review. No TLS connections or renewal actions."""
import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone


ASSETS = {
    "CERT-DEMO-01": {
        "source": "inventory-cert-demo-01",
        "service": "synthetic-checkout",
        "observed_at": "2026-10-20T13:00:00+00:00",
        "not_before": "2026-07-23T00:00:00+00:00",
        "not_after": "2026-10-23T13:00:00+00:00",
        "snapshot_cert_id": "synthetic-cert-old-01",
        "renewal": {"source": "renewal-record-demo-01", "status": "issued",
                    "issued_cert_id": "synthetic-cert-new-02",
                    "deployed_cert_id": None, "deployment_checked_at": None},
    }
}
POLICY = {"source": "renewal-policy-demo-01", "warning_days": 14,
          "critical_hours": 72, "max_snapshot_age_hours": 24,
          "rule": "Review expiry and freshness separately; issued is not deployed."}


def instant(value):
    """Require an explicit UTC offset; normalize before elapsed-time comparisons."""
    if not isinstance(value, str):
        raise ValueError("Timestamp must be text with UTC offset")
    result = datetime.fromisoformat(value)
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("Timezone required")
    return result.astimezone(timezone.utc)


def assess(asset, as_of):
    reference = instant(as_of)
    observed = instant(asset["observed_at"])
    start, end = instant(asset["not_before"]), instant(asset["not_after"])
    if end <= start:
        raise ValueError("Invalid validity interval")
    age = reference - observed
    if age < timedelta(0):
        freshness = "future_snapshot"
    elif age > timedelta(hours=POLICY["max_snapshot_age_hours"]):
        freshness = "stale_snapshot"
    else:
        freshness = "fresh_snapshot"
    remaining = end - reference
    if reference < start:
        urgency = "not_yet_valid"
    elif remaining <= timedelta(0):
        urgency = "expired"
    elif remaining <= timedelta(hours=POLICY["critical_hours"]):
        urgency = "critical"
    elif remaining <= timedelta(days=POLICY["warning_days"]):
        urgency = "warning"
    else:
        urgency = "outside_warning_window"
    # These records are administrative evidence, never a live TLS observation.
    renewal = asset["renewal"]
    deployed = renewal.get("deployed_cert_id")
    recorded = bool(deployed and deployed == renewal.get("issued_cert_id")
                    and renewal.get("deployment_checked_at"))
    return {"source": "assessment-cert-demo-01", "as_of": reference.isoformat(),
            "inputs": [asset["source"], renewal["source"], POLICY["source"]],
            "seconds_to_snapshot_expiry": int(remaining.total_seconds()),
            "snapshot_age_seconds": int(age.total_seconds()),
            "snapshot_freshness": freshness, "snapshot_urgency": urgency,
            "renewal_status": renewal["status"],
            "replacement_deployment": "recorded_requires_live_check" if recorded else "unconfirmed",
            "current_endpoint_status": "unknown", "human_review_required": True,
            "actions_executed": False}


def tools():
    descriptions = {
        "lookup_certificate": "Read synthetic inventory and time evidence; not a live TLS scan",
        "lookup_renewal": "Read synthetic renewal record and policy; issuance is not deployment",
        "assess_expiry": "Compute snapshot freshness and expiry urgency at the supplied reference time",
    }
    return [{"type": "function", "function": {"name": name, "description": description,
             "parameters": {"type": "object", "properties": {"asset_id": {"type": "string"}},
                            "required": ["asset_id"], "additionalProperties": False}}}
            for name, description in descriptions.items()]


def execute(name, arguments, asset_id, as_of):
    if (name not in {t["function"]["name"] for t in tools()}
            or not isinstance(arguments, dict) or set(arguments) != {"asset_id"}
            or arguments["asset_id"] != asset_id):
        raise ValueError("Invalid tool or asset scope")
    asset = ASSETS.get(asset_id)
    if asset is None:
        raise ValueError("Unknown synthetic asset; supply CERT-DEMO-01")
    if name == "lookup_certificate":
        return [{key: value for key, value in asset.items() if key != "renewal"}]
    if name == "lookup_renewal":
        return [asset["renewal"], POLICY]
    return [assess(asset, as_of)]


def chat(messages):
    payload = {"model": os.environ.get("OLLAMA_MODEL", "qwen3:4b"), "messages": messages,
               "tools": tools(), "stream": False, "think": True,
               "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 2500}}
    request = urllib.request.Request("http://127.0.0.1:11434/api/chat",
                                    data=json.dumps(payload).encode(),
                                    headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)["message"]
