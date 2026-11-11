"""Prioritize a fixed, synthetic backlog for a single production line."""
import json
import os
import urllib.request
from datetime import datetime, timezone

POLICY = {"source": "rework-policy-demo-01", "line_id": "LINE-DEMO-A",
          "order": ["severity descending", "due time ascending", "job ID ascending"]}
BACKLOG = {"source": "rework-jobs-demo-01", "line_id": "LINE-DEMO-A",
           "captured_at": "2026-11-11T15:00:00Z", "jobs": [
    {"job_id": "RW-001", "severity": 1, "due_at": "2026-11-11T14:00:00Z"},
    {"job_id": "RW-002", "severity": 2, "due_at": "2026-11-11T11:00:00-05:00"},
    {"job_id": "RW-003", "severity": 2, "due_at": "2026-11-11T16:00:00Z"},
    {"job_id": "RW-004", "severity": None, "due_at": None},
]}


def instant(value):
    if not isinstance(value, str):
        raise ValueError("Timestamp text required")
    parsed = datetime.fromisoformat(value)
    if parsed.utcoffset() is None:
        raise ValueError("Explicit offset required")
    return parsed.astimezone(timezone.utc)


def rank(backlog, as_of):
    reference = instant(as_of)
    if instant(backlog["captured_at"]) > reference:
        raise ValueError("Future backlog snapshot")
    jobs = backlog["jobs"]
    if not isinstance(jobs, list) or len(jobs) > 100:
        raise ValueError("At most 100 jobs")
    seen, candidates, incomplete = set(), [], []
    for job in jobs:
        if not isinstance(job, dict) or set(job) != {"job_id", "severity", "due_at"}:
            raise ValueError("Invalid job fields")
        job_id, severity, due_at = job["job_id"], job["severity"], job["due_at"]
        if not isinstance(job_id, str) or not job_id.strip() or job_id in seen:
            raise ValueError("Invalid or duplicate job ID")
        seen.add(job_id)
        if severity is not None and (type(severity) is not int or not 1 <= severity <= 3):
            raise ValueError("Expected integer severity 1 to 3")
        due = instant(due_at) if due_at is not None else None
        if severity is None or due is None:
            incomplete.append({**job, "missing": [
                name for name in ("severity", "due_at") if job[name] is None
            ]})
            continue
        key = (-severity, due, job_id)
        candidates.append((key, {**job, "due_utc": due.isoformat(), "overdue": due < reference}))
    ordered = [job for _, job in sorted(candidates, key=lambda item: item[0])]
    return {"source": "priority-assessment-demo-01", "inputs": [POLICY["source"], backlog["source"]],
            "ordered": ordered, "needs_evidence": incomplete, "dispatch_authorized": False}


def tools():
    descriptions = {"lookup_policy": "Read the synthetic line ranking policy",
                    "lookup_jobs": "Read the line backlog and snapshot time",
                    "rank_jobs": "Compute stable order, overdue flags and missing evidence"}
    return [{"type": "function", "function": {"name": name, "description": description,
             "parameters": {"type": "object", "properties": {"line_id": {"type": "string"}},
                            "required": ["line_id"], "additionalProperties": False}}}
            for name, description in descriptions.items()]


def execute(name, arguments, line_id, as_of):
    if (name not in {"lookup_policy", "lookup_jobs", "rank_jobs"}
            or arguments != {"line_id": line_id} or line_id != POLICY["line_id"]
            or line_id != BACKLOG["line_id"]):
        raise ValueError("Invalid tool or line scope")
    if name == "lookup_policy":
        return [POLICY]
    if name == "lookup_jobs":
        return [BACKLOG]
    return [rank(BACKLOG, as_of)]


def chat(messages):
    payload = {"model": os.environ.get("OLLAMA_MODEL", "qwen3:4b"), "messages": messages,
               "tools": tools(), "stream": False, "think": True,
               "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 2500}}
    request = urllib.request.Request("http://127.0.0.1:11434/api/chat", data=json.dumps(payload).encode(),
                                    headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)["message"]
