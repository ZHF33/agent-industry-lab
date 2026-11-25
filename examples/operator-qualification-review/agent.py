"""Propose maximum-count job/operator matching from a fixed synthetic snapshot."""
import json
import os
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

POLICY = {
    "source": "qualification-policy-demo-01",
    "plan_id": "PLAN-DEMO-A",
    "issued_at": "2026-11-25T12:30:00Z",
    "max_age_seconds": 60,
    "jobs": [
        {"job_id": "J-01", "required_skills": ["PACK"]},
        {"job_id": "J-02", "required_skills": ["LABEL"]},
        {"job_id": "J-03", "required_skills": ["SCAN"]},
    ],
}
OPERATORS_PATH = Path(__file__).with_name("operators.json")

def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def load_snapshot():
    return json.loads(OPERATORS_PATH.read_text(encoding="utf-8"), object_pairs_hook=unique_object)


def instant(value):
    if not isinstance(value, str):
        raise ValueError("Timestamp text required")
    parsed = datetime.fromisoformat(value)
    if parsed.utcoffset() is None:
        raise ValueError("Explicit offset required")
    return parsed.astimezone(timezone.utc)


def validate_scope(snapshot, policy, plan_id, as_of):
    cutoff = instant(as_of)
    for evidence in (snapshot, policy):
        if evidence["plan_id"] != plan_id or instant(evidence["issued_at"]) > cutoff:
            raise ValueError("Evidence is out of scope or newer than review time")


def identifier(value):
    if not isinstance(value, str) or re.fullmatch(r"[A-Za-z0-9_-]{1,32}", value) is None:
        raise ValueError("Expected ASCII identifier up to 32 characters")
    return value


def skills(values, allow_empty=False):
    minimum = 0 if allow_empty else 1
    if not isinstance(values, list) or not minimum <= len(values) <= 8:
        raise ValueError("Expected bounded list of skill identifiers")
    checked = [identifier(value) for value in values]
    if len(set(checked)) != len(checked):
        raise ValueError("Duplicate skill identifiers")
    return set(checked)


def maximum_matching(eligible):
    # Internal input: validated job IDs mapped to sorted unique operator IDs.
    owner = {}
    attempts = []

    def pairs():
        return sorted([{"job_id": job, "operator_id": operator}
                       for operator, job in owner.items()], key=lambda row: row["job_id"])

    def augment(job, seen):
        for operator in eligible[job]:
            if operator in seen:
                continue
            seen.add(operator)
            if operator not in owner or augment(owner[operator], seen):
                owner[operator] = job
                return True
        return False

    for job in sorted(eligible):
        before = pairs()
        success = augment(job, set())
        attempts.append({"job_id": job, "increased_count": success,
                         "before": before, "after": pairs()})
    return pairs(), attempts


def assess(snapshot, policy, as_of):
    validate_scope(snapshot, policy, policy["plan_id"], as_of)
    age = (instant(as_of) - instant(snapshot["issued_at"])).total_seconds()
    limit = policy["max_age_seconds"]
    if type(limit) is not int or not 1 <= limit <= 3600 or age > limit:
        raise ValueError("Invalid age policy or stale operator snapshot")
    if snapshot["declared_complete"] is not True:
        raise ValueError("Complete snapshot declaration required")
    jobs, operators = policy["jobs"], snapshot["operators"]
    if not isinstance(jobs, list) or not 1 <= len(jobs) <= 8:
        raise ValueError("Expected 1 to 8 jobs")
    if not isinstance(operators, list) or len(operators) > 8:
        raise ValueError("Expected at most 8 operators")
    requirements, available, seen = {}, {}, set()
    for row in jobs:
        if not isinstance(row, dict) or set(row) != {"job_id", "required_skills"}:
            raise ValueError("Invalid job fields")
        job = identifier(row["job_id"])
        if job in requirements:
            raise ValueError("Duplicate job ID")
        requirements[job] = skills(row["required_skills"])
    for row in operators:
        if not isinstance(row, dict) or set(row) != {"operator_id", "approved_skills", "available"}:
            raise ValueError("Invalid operator fields")
        operator = identifier(row["operator_id"])
        if operator in seen or type(row["available"]) is not bool:
            raise ValueError("Duplicate operator or invalid availability flag")
        seen.add(operator)
        approved = skills(row["approved_skills"], allow_empty=True)
        if row["available"]:
            available[operator] = approved
    eligible = {job: sorted(operator for operator, approved in available.items() if needed <= approved)
                for job, needed in sorted(requirements.items())}
    pairs, attempts = maximum_matching(eligible)
    assigned_jobs = {row["job_id"] for row in pairs}
    return {"source": "qualification-match-demo-01", "inputs": [snapshot["source"], policy["source"]],
            "plan_id": policy["plan_id"], "method": "augmenting-path-dfs-v1",
            "eligible": eligible, "pairs": pairs, "attempts": attempts,
            "matched_count": len(pairs), "job_count": len(jobs),
            "unmatched_jobs": sorted(set(requirements) - assigned_jobs),
            "status": "full_proposal" if len(pairs) == len(jobs) else "partial_proposal",
            "roster_actions_executed": False}


TOOL_DESCRIPTIONS = {
    "lookup_policy": "Read fixed job requirements, one-person-per-job contract and freshness policy",
    "lookup_operators": "Read fixed synthetic approved skills and availability snapshot",
    "match_operators": "Find a maximum-count one-to-one eligible matching and expose reassignment steps and unmatched jobs",
}

def tools():
    return [{"type": "function", "function": {"name": name, "description": description,
             "parameters": {"type": "object", "properties": {"plan_id": {"type": "string"}},
                            "required": ["plan_id"], "additionalProperties": False}}}
            for name, description in TOOL_DESCRIPTIONS.items()]


def execute(name, arguments, plan_id, as_of, snapshot):
    if name not in TOOL_DESCRIPTIONS or arguments != {"plan_id": plan_id}:
        raise ValueError("Invalid tool or plan argument")
    validate_scope(snapshot, POLICY, plan_id, as_of)
    if name == "lookup_policy":
        return [POLICY]
    if name == "lookup_operators":
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
