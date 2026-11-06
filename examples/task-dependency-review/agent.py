"""Synthetic manufacturing task dependencies, read-only evidence review."""
import json
import os
import re
import urllib.request
from datetime import datetime, timezone
from graphlib import TopologicalSorter, CycleError

PLAN = {"source": "plan-demo-01", "plan_id": "PLAN-DEMO-A", "revision": 2}
TASKS = {"source": "tasks-demo-01", "plan_id": "PLAN-DEMO-A", "revision": 2,
         "observed_at": "2026-11-06T12:00:00Z", "entries": [
             {"task_id": "TASK-A", "status": "done", "requires": []},
             {"task_id": "TASK-B", "status": "pending", "requires": ["TASK-A"]},
             {"task_id": "TASK-C", "status": "pending", "requires": ["TASK-B"]},
             {"task_id": "TASK-D", "status": "running", "requires": ["TASK-A"]}]}
POLICY = {"source": "dependency-policy-demo-01", "max_tasks": 100, "max_edges": 500,
          "max_age_seconds": 60}


def instant(value):
    if not isinstance(value, str):
        raise ValueError("Timestamp text required")
    parsed = datetime.fromisoformat(value)
    if parsed.utcoffset() is None:
        raise ValueError("Explicit offset required")
    return parsed.astimezone(timezone.utc)


def inspect_dependencies(entries):
    if not isinstance(entries, list) or not 1 <= len(entries) <= POLICY["max_tasks"]:
        raise ValueError("Need 1–100 tasks")
    tasks = {}
    edge_count = 0
    for row in entries:
        if not isinstance(row, dict) or set(row) != {"task_id", "status", "requires"}:
            raise ValueError("Invalid task fields")
        identity = row["task_id"]
        if not isinstance(identity, str) or not re.fullmatch(r"[A-Z0-9-]{1,80}", identity) or identity in tasks:
            raise ValueError("Unique task ID required")
        if row["status"] not in ("pending", "running", "done"):
            raise ValueError("Invalid status")
        requires = row["requires"]
        if (not isinstance(requires, list) or len(requires) > POLICY["max_tasks"]
                or any(not isinstance(value, str) for value in requires)
                or len(set(requires)) != len(requires)):
            raise ValueError("Distinct prerequisite IDs required")
        edge_count += len(requires)
        tasks[identity] = row
    if edge_count > POLICY["max_edges"]:
        raise ValueError("Too many dependency edges")
    if any(dep not in tasks for row in tasks.values() for dep in row["requires"]):
        raise ValueError("Unknown prerequisite")
    predecessors = {key: tuple(sorted(tasks[key]["requires"])) for key in sorted(tasks)}
    cycle = []
    try:
        order = list(TopologicalSorter(predecessors).static_order())
    except CycleError as error:
        order = []
        cycle = list(error.args[1])
    waiting, inconsistent, ready = [], [], []
    for key in sorted(tasks):
        row = tasks[key]
        unfinished = [dep for dep in sorted(row["requires"]) if tasks[dep]["status"] != "done"]
        if row["status"] == "pending":
            if unfinished:
                waiting.append({"task_id": key, "unfinished_predecessors": unfinished})
            elif not cycle:
                ready.append(key)
        elif unfinished:
            inconsistent.append({"task_id": key, "status": row["status"],
                                 "unfinished_predecessors": unfinished})
    return {"structural_order": order, "cycle_example": cycle,
            "ready_pending_tasks": ready, "waiting_tasks": waiting,
            "inconsistent_active_or_done": inconsistent}


def assess(plan, evidence, as_of):
    if plan["plan_id"] != evidence["plan_id"]:
        raise ValueError("Plan identity mismatch")
    for revision in (plan["revision"], evidence["revision"]):
        if type(revision) is not int or revision < 1:
            raise ValueError("Positive integer revisions required")
    observed, reference = instant(evidence["observed_at"]), instant(as_of)
    if observed > reference:
        raise ValueError("Future evidence")
    result = inspect_dependencies(evidence["entries"])
    limitations = []
    if plan["revision"] != evidence["revision"]:
        limitations.append("revision_mismatch")
    if (reference - observed).total_seconds() > POLICY["max_age_seconds"]:
        limitations.append("stale_evidence")
    return {"source": "dependency-assessment-demo-01", **result, "limitations": limitations,
            "inputs": [plan["source"], evidence["source"], POLICY["source"]],
            "dispatch_authorized": False, "actions_executed": False}


def tools():
    descriptions = {"lookup_plan": "Read scoped synthetic plan revision and review limits",
                    "lookup_tasks": "Read task status and prerequisite snapshot",
                    "assess_dependencies": "Find structural order, cycle example and current prerequisite blockers"}
    return [{"type": "function", "function": {"name": name, "description": description,
             "parameters": {"type": "object", "properties": {"plan_id": {"type": "string"}},
                            "required": ["plan_id"], "additionalProperties": False}}}
            for name, description in descriptions.items()]


def execute(name, arguments, plan_id, as_of):
    if (name not in {"lookup_plan", "lookup_tasks", "assess_dependencies"}
            or arguments != {"plan_id": plan_id} or plan_id != PLAN["plan_id"]):
        raise ValueError("Invalid tool or plan scope")
    if name == "lookup_plan":
        return [PLAN, POLICY]
    if name == "lookup_tasks":
        return [TASKS]
    return [assess(PLAN, TASKS, as_of)]


def chat(messages):
    payload = {"model": os.environ.get("OLLAMA_MODEL", "qwen3:4b"), "messages": messages,
               "tools": tools(), "stream": False, "think": True,
               "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 2500}}
    request = urllib.request.Request("http://127.0.0.1:11434/api/chat", data=json.dumps(payload).encode(),
                                    headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)["message"]
