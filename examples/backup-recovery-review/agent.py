"""Synthetic recovery evidence only. Never reads, backs up or restores a database."""
import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone


SYSTEMS = {"RECOVERY-DEMO-01": {
    "source": "backup-manifest-demo-01", "service": "synthetic-order-service",
    "backup_id": "BACKUP-DEMO-01", "status": "completed",
    "recovery_point_at": "2026-10-21T12:50:00+00:00",
    "completed_at": "2026-10-21T13:00:00+00:00",
    "observed_at": "2026-10-21T13:04:00+00:00",
    "checksum_recorded_match": True,
    "drill": {"source": "restore-drill-demo-01", "status": "passed",
              "started_at": "2026-09-01T12:00:00+00:00",
              "service_ready_at": "2026-09-01T12:22:00+00:00",
              "observed_at": "2026-09-01T12:25:00+00:00",
              "tested_backup_id": "BACKUP-DEMO-OLD-01",
              "scenario": "isolated synthetic recovery rehearsal"}}}
POLICY = {"source": "recovery-policy-demo-01", "rpo_seconds": 900,
          "rto_seconds": 1800, "drill_max_age_days": 30,
          "manifest_max_age_seconds": 3600}


def instant(value):
    if not isinstance(value, str):
        raise ValueError("Timestamp text required")
    result = datetime.fromisoformat(value)
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("Timezone required")
    return result.astimezone(timezone.utc)


def assess(record, as_of):
    reference = instant(as_of)
    point = instant(record["recovery_point_at"])
    completed = instant(record["completed_at"])
    observed = instant(record["observed_at"])
    if not point <= completed <= observed:
        raise ValueError("Inconsistent backup timeline")
    drill = record["drill"]
    started = instant(drill["started_at"])
    ready = instant(drill["service_ready_at"])
    drill_observed = instant(drill["observed_at"])
    if not started <= ready <= drill_observed:
        raise ValueError("Inconsistent drill timeline")
    if observed > reference or drill_observed > reference:
        raise ValueError("Future evidence cannot describe the reference time")
    lag = (reference - point).total_seconds()
    duration = (ready - started).total_seconds()
    manifest_fresh = reference - observed <= timedelta(seconds=POLICY["manifest_max_age_seconds"])
    drill_fresh = reference - drill_observed <= timedelta(days=POLICY["drill_max_age_days"])
    # Only classify recorded metadata; no archive-chain, keys or live restore validation.
    rpo = ("recorded_point_within_target" if lag <= POLICY["rpo_seconds"]
           else "recorded_point_exceeds_target") if record["status"] == "completed" and manifest_fresh else "insufficient_evidence"
    historical_rto = ("within_target" if duration <= POLICY["rto_seconds"] else "exceeds_target") if drill["status"] == "passed" else "insufficient_evidence"
    gaps = []
    if rpo != "recorded_point_within_target":
        gaps.append("recovery_point_target_not_supported")
    if not drill_fresh:
        gaps.append("restore_drill_stale")
    if historical_rto != "within_target":
        gaps.append("historical_service_ready_target_not_supported")
    if drill["tested_backup_id"] != record["backup_id"]:
        gaps.append("latest_backup_not_tested_by_recorded_drill")
    if record["checksum_recorded_match"] is not True:
        gaps.append("checksum_match_not_recorded")
    return {"source": "recovery-assessment-demo-01",
            "inputs": [record["source"], drill["source"], POLICY["source"]],
            "as_of": reference.isoformat(), "recorded_point_lag_seconds": lag,
            "recorded_service_ready_seconds": duration,
            "manifest_fresh": manifest_fresh, "drill_fresh": drill_fresh,
            "rpo_evidence": rpo, "historical_rto_evidence": historical_rto,
            "gaps": gaps, "latest_backup_restore_status": "unknown",
            "actual_recoverability": "unknown", "human_review_required": True,
            "actions_executed": False}


def tools():
    descriptions = {
        "lookup_backup": "Read synthetic manifest and recorded recovery point, not database files",
        "lookup_restore_drill": "Read historical synthetic service-ready rehearsal and target policy",
        "assess_recovery": "Compare recorded point lag, drill duration, recency and backup identity; actual recoverability stays unknown",
    }
    return [{"type": "function", "function": {"name": name, "description": description,
             "parameters": {"type": "object", "properties": {"system_id": {"type": "string"}},
                            "required": ["system_id"], "additionalProperties": False}}}
            for name, description in descriptions.items()]


def execute(name, arguments, system_id, as_of):
    if (name not in {t["function"]["name"] for t in tools()}
            or not isinstance(arguments, dict) or set(arguments) != {"system_id"}
            or arguments["system_id"] != system_id):
        raise ValueError("Invalid tool or system scope")
    record = SYSTEMS.get(system_id)
    if record is None:
        raise ValueError("Unknown synthetic system")
    if name == "lookup_backup":
        return [{key: value for key, value in record.items() if key != "drill"}]
    if name == "lookup_restore_drill":
        return [record["drill"], POLICY]
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
