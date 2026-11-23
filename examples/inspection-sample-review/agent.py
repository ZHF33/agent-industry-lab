"""Build a reproducible stratified inspection list from a fixed synthetic population."""
import hashlib
import json
import os
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

POLICY = {
    "source": "sampling-policy-demo-01",
    "batch_id": "BATCH-DEMO-A",
    "issued_at": "2026-11-23T12:30:00Z",
    "algorithm": "sha256-json-array-v1",
    "seed": "review-demo-01",
    "quotas": {"A": 2, "B": 2},
}
POPULATION_PATH = Path(__file__).with_name("population.json")

def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def load_snapshot():
    return json.loads(POPULATION_PATH.read_text(encoding="utf-8"), object_pairs_hook=unique_object)


def instant(value):
    if not isinstance(value, str):
        raise ValueError("Timestamp text required")
    parsed = datetime.fromisoformat(value)
    if parsed.utcoffset() is None:
        raise ValueError("Explicit offset required")
    return parsed.astimezone(timezone.utc)


def validate_scope(snapshot, policy, batch_id, as_of):
    cutoff = instant(as_of)
    for evidence in (snapshot, policy):
        if evidence["batch_id"] != batch_id or instant(evidence["issued_at"]) > cutoff:
            raise ValueError("Evidence is out of scope or newer than review time")


def identifier(value):
    if not isinstance(value, str) or re.fullmatch(r"[A-Za-z0-9_-]{1,64}", value) is None:
        raise ValueError("Expected an ASCII identifier up to 64 characters")
    return value


def score(seed, batch_id, stratum, unit_id):
    # Versioned, unambiguous bytes; never use Python hash() for persisted selection.
    text = json.dumps([seed, batch_id, stratum, unit_id], ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def assess(snapshot, policy, as_of):
    validate_scope(snapshot, policy, policy["batch_id"], as_of)
    if policy["algorithm"] != "sha256-json-array-v1":
        raise ValueError("Unsupported sampling algorithm")
    identifier(policy["seed"])
    identifier(policy["batch_id"])
    quotas = policy["quotas"]
    if not isinstance(quotas, dict) or not 1 <= len(quotas) <= 20:
        raise ValueError("Expected 1 to 20 independently approved stratum quotas")
    for stratum, quota in quotas.items():
        identifier(stratum)
        if type(quota) is not int or not 1 <= quota <= 1000:
            raise ValueError("Expected positive integer quota up to 1000")
    units = snapshot["units"]
    if not isinstance(units, list) or len(units) > 1000:
        raise ValueError("Expected at most 1000 population units")
    groups, seen = {key: [] for key in quotas}, set()
    for unit in units:
        if not isinstance(unit, dict) or set(unit) != {"unit_id", "stratum"}:
            raise ValueError("Invalid population fields")
        unit_id, stratum = identifier(unit["unit_id"]), identifier(unit["stratum"])
        if unit_id in seen or stratum not in quotas:
            raise ValueError("Duplicate unit ID or stratum without quota")
        seen.add(unit_id)
        groups[stratum].append({"unit_id": unit_id, "score": score(
            policy["seed"], policy["batch_id"], stratum, unit_id)})
    strata = []
    for stratum, quota in sorted(quotas.items()):
        ranked = sorted(groups[stratum], key=lambda row: (row["score"], row["unit_id"]))
        chosen = ranked[:quota]
        strata.append({"stratum": stratum, "available": len(ranked), "requested": quota,
                       "selected": chosen, "shortage": max(0, quota-len(ranked))})
    return {"source": "sampling-plan-demo-01",
            "inputs": [snapshot["source"], policy["source"]],
            "batch_id": policy["batch_id"], "algorithm": policy["algorithm"], "seed": policy["seed"],
            "population_count": len(units), "strata": strata,
            "requested_count": sum(quotas.values()),
            "selected_count": sum(len(row["selected"]) for row in strata),
            "status": "short_population" if any(row["shortage"] for row in strata) else "proposed",
            "quality_acceptance": False}


TOOL_DESCRIPTIONS = {
    "lookup_policy": "Read fixed independently supplied per-stratum quotas and selection seed",
    "lookup_population": "Read the bounded synthetic population of uniquely identified units",
    "plan_sample": "Build deterministic per-stratum sample lists with SHA-256 scores and quota shortages",
}

def tools():
    return [{"type": "function", "function": {"name": name, "description": description,
             "parameters": {"type": "object", "properties": {"batch_id": {"type": "string"}},
                            "required": ["batch_id"], "additionalProperties": False}}}
            for name, description in TOOL_DESCRIPTIONS.items()]


def execute(name, arguments, batch_id, as_of, snapshot):
    if name not in TOOL_DESCRIPTIONS or arguments != {"batch_id": batch_id}:
        raise ValueError("Invalid tool or batch argument")
    validate_scope(snapshot, POLICY, batch_id, as_of)
    if name == "lookup_policy":
        return [POLICY]
    if name == "lookup_population":
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
