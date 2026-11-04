"""Review evidence for a synthetic handover window using half-open intervals."""
import json
import os
import urllib.request
from datetime import datetime, timezone

SHIFT = {"source": "shift-demo-01", "shift_id": "SHIFT-DEMO-A",
         "start": "2026-11-04T08:00:00Z", "end": "2026-11-04T12:00:00Z"}
EVIDENCE = {"source": "coverage-demo-01", "shift_id": "SHIFT-DEMO-A",
            "observed_at": "2026-11-04T13:00:00Z", "declared_complete": True,
            "entries": [
                {"source": "record-A", "start": "2026-11-04T07:50:00Z", "end": "2026-11-04T09:00:00Z"},
                {"source": "record-B", "start": "2026-11-04T08:45:00Z", "end": "2026-11-04T10:00:00Z"},
                {"source": "record-C", "start": "2026-11-04T10:20:00Z", "end": "2026-11-04T12:10:00Z"}]}
POLICY = {"source": "coverage-policy-demo-01", "max_age_seconds": 60, "max_entries": 100}


def instant(value):
    if not isinstance(value, str):
        raise ValueError("Timestamp text required")
    parsed = datetime.fromisoformat(value)
    if parsed.utcoffset() is None:
        raise ValueError("Explicit offset required")
    return parsed.astimezone(timezone.utc)


def coverage(start, end, entries):
    left, right = instant(start), instant(end)
    if left >= right or not isinstance(entries, list) or len(entries) > POLICY["max_entries"]:
        raise ValueError("Invalid window or entry count")
    clipped, seen = [], set()
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"source", "start", "end"}:
            raise ValueError("Invalid interval fields")
        source = entry["source"]
        if not isinstance(source, str) or not source.strip() or source in seen:
            raise ValueError("Distinct source IDs required")
        seen.add(source)
        a, b = instant(entry["start"]), instant(entry["end"])
        if a >= b:
            raise ValueError("Interval must have positive length")
        a, b = max(a, left), min(b, right)
        if a < b:
            clipped.append((a, b, source))

    merged = []
    for a, b, source in sorted(clipped):
        if merged and a <= merged[-1][1]:
            first, last, sources = merged[-1]
            merged[-1] = (first, max(last, b), sources + [source])
        else:
            merged.append((a, b, [source]))

    def segment(a, b):
        return {"start": a.isoformat(), "end": b.isoformat(),
                "seconds": (b - a).total_seconds()}

    covered, gaps, cursor = [], [], left
    for a, b, sources in merged:
        if cursor < a:
            gaps.append(segment(cursor, a))
        covered.append({**segment(a, b), "sources": sources})
        cursor = b
    if cursor < right:
        gaps.append(segment(cursor, right))
    return {"covered": covered, "gaps": gaps,
            "covered_seconds": sum(row["seconds"] for row in covered),
            "gap_seconds": sum(row["seconds"] for row in gaps)}


def assess(shift, evidence, as_of):
    if shift["shift_id"] != evidence["shift_id"] or type(evidence["declared_complete"]) is not bool:
        raise ValueError("Evidence identity or coverage declaration invalid")
    observed, reference = instant(evidence["observed_at"]), instant(as_of)
    if not instant(shift["end"]) <= observed <= reference:
        raise ValueError("A closed shift and nonfuture snapshot are required")
    if any(instant(row["end"]) > observed for row in evidence["entries"]):
        raise ValueError("Entry ends after snapshot")
    result = coverage(shift["start"], shift["end"], evidence["entries"])
    limitations = []
    if (reference - observed).total_seconds() > POLICY["max_age_seconds"]:
        limitations.append("stale_snapshot")
    if not evidence["declared_complete"]:
        limitations.append("source_declares_incomplete")
    return {"source": "coverage-assessment-demo-01", **result,
            "limitations": limitations, "actions_executed": False}


def tools():
    descriptions = {"lookup_shift": "Read the synthetic handover window and evidence policy",
                    "lookup_coverage": "Read the synthetic interval evidence snapshot",
                    "assess_coverage": "Clip and merge interval evidence and report coverage gaps"}
    return [{"type": "function", "function": {"name": name, "description": description,
             "parameters": {"type": "object", "properties": {"shift_id": {"type": "string"}},
                            "required": ["shift_id"], "additionalProperties": False}}}
            for name, description in descriptions.items()]


def execute(name, arguments, shift_id, as_of):
    if (name not in {"lookup_shift", "lookup_coverage", "assess_coverage"}
            or arguments != {"shift_id": shift_id} or shift_id != SHIFT["shift_id"]):
        raise ValueError("Invalid tool or shift scope")
    if name == "lookup_shift":
        return [SHIFT, POLICY]
    if name == "lookup_coverage":
        return [EVIDENCE]
    return [assess(SHIFT, EVIDENCE, as_of)]


def chat(messages):
    payload = {"model": os.environ.get("OLLAMA_MODEL", "qwen3:4b"), "messages": messages,
               "tools": tools(), "stream": False, "think": True,
               "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 2500}}
    request = urllib.request.Request("http://127.0.0.1:11434/api/chat", data=json.dumps(payload).encode(),
                                    headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)["message"]
