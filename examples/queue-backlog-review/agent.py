"""Synthetic queue telemetry review, without a broker connection or control actions."""
import json
import os
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal


QUEUES = {"QUEUE-DEMO-01": {
    "source": "queue-snapshot-demo-01", "queue": "synthetic-label-jobs",
    "window_start": "2026-10-22T12:50:00+00:00",
    "window_end": "2026-10-22T12:55:00+00:00",
    "observed_at": "2026-10-22T12:55:00+00:00",
    "ready_start": 100, "ready_end": 250, "unacked_start": 20, "unacked_end": 50,
    "published": 600, "acked": 420, "expired": 0, "purged": 0,
    "dead_lettered_out": 0, "consumers": 2,
    "oldest_ready_age_seconds": 480,
    "worker": {"source": "worker-observation-demo-01",
               "observed_at": "2026-10-22T12:55:00+00:00",
               "reported_errors": ["synthetic downstream throttling"],
               "root_cause": "unknown", "duplicate_effects_checked": False}
}}
POLICY = {"source": "queue-policy-demo-01", "max_age_seconds": 120,
          "warning_oldest_ready_seconds": 300,
          "counter_scope": "One stable queue generation; publishes accepted into queue, acks remove in-flight deliveries; no retries or reset in this synthetic interval"}
COUNT_FIELDS = ("ready_start", "ready_end", "unacked_start", "unacked_end", "published",
                "acked", "expired", "purged", "dead_lettered_out", "consumers", "oldest_ready_age_seconds")


def instant(value):
    if not isinstance(value, str):
        raise ValueError("Timestamp text required")
    result = datetime.fromisoformat(value)
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("Timezone required")
    return result.astimezone(timezone.utc)


def assess(record, as_of):
    for key in COUNT_FIELDS:
        if type(record[key]) is not int or record[key] < 0:
            raise ValueError("Non-negative integer counters required")
    start, end, observed = (instant(record[key]) for key in ("window_start", "window_end", "observed_at"))
    reference = instant(as_of)
    if not start < end <= observed <= reference:
        raise ValueError("Invalid or future observation interval")
    duration = Decimal(str((end - start).total_seconds()))
    total_start = record["ready_start"] + record["unacked_start"]
    total_end = record["ready_end"] + record["unacked_end"]
    expected = total_start + record["published"] - record["acked"] - record["expired"] - record["purged"] - record["dead_lettered_out"]
    gap = total_end - expected
    fresh = (reference - observed).total_seconds() <= POLICY["max_age_seconds"]
    valid = gap == 0
    arrival = Decimal(record["published"]) / duration
    completion = Decimal(record["acked"]) / duration
    net = arrival - completion
    # Pure what-if: no new arrivals, same ack throughput, no other removals.
    drain = str((Decimal(total_end) / completion).quantize(Decimal("0.01"))) if completion > 0 and valid and fresh else None
    warnings = []
    if not fresh:
        warnings.append("stale_queue_snapshot")
    if not valid:
        warnings.append("counter_balance_mismatch")
    if record["consumers"] == 0 and total_end:
        warnings.append("no_consumers_recorded")
    if record["oldest_ready_age_seconds"] >= POLICY["warning_oldest_ready_seconds"]:
        warnings.append("oldest_ready_age_over_target")
    if valid and fresh and net > 0:
        warnings.append("arrival_rate_exceeds_ack_rate")
    return {"source": "queue-assessment-demo-01", "inputs": [record["source"], POLICY["source"]],
            "as_of": reference.isoformat(), "window_seconds": str(duration),
            "total_start": total_start, "total_end": total_end, "counter_balance_gap": gap,
            "counters_consistent": valid, "snapshot_fresh": fresh,
            "published_per_second": str(arrival), "acked_per_second": str(completion),
            "net_published_minus_acked_per_second": str(net),
            "zero_arrival_drain_seconds_estimate": drain,
            "estimate_assumptions": "Zero new arrivals, unchanged ack throughput, valid matched counters; illustrative, not ETA or SLA",
            "warnings": warnings, "root_cause": "unknown",
            "business_effects_verified": False, "actions_executed": False}


def tools():
    descriptions = {
        "lookup_queue": "Read fixed synthetic ready/unacked snapshots and interval counters",
        "lookup_workers": "Read synthetic worker observation and policy, not proof of root cause",
        "assess_backlog": "Check counter balance/freshness and compare interval arrival/ack rates; zero-arrival scenario is not an ETA",
    }
    return [{"type": "function", "function": {"name": name, "description": description,
             "parameters": {"type": "object", "properties": {"queue_id": {"type": "string"}},
                            "required": ["queue_id"], "additionalProperties": False}}}
            for name, description in descriptions.items()]


def execute(name, arguments, queue_id, as_of):
    if (name not in {t["function"]["name"] for t in tools()}
            or not isinstance(arguments, dict) or set(arguments) != {"queue_id"}
            or arguments["queue_id"] != queue_id):
        raise ValueError("Invalid tool or queue scope")
    record = QUEUES.get(queue_id)
    if record is None:
        raise ValueError("Unknown synthetic queue")
    if name == "lookup_queue":
        return [{key: value for key, value in record.items() if key != "worker"}]
    if name == "lookup_workers":
        return [record["worker"], POLICY]
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
