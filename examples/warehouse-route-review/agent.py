"""Bounded directed warehouse routing from a synthetic open-aisle snapshot."""
import heapq
import json
import os
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

POLICY = {"source": "route-policy-demo-01", "map_id": "MAP-DEMO-A",
          "issued_at": "2026-11-27T12:30:00Z", "start": "ENTRY", "goal": "EXIT",
          "unit": "m", "max_age_seconds": 60}
MAP_PATH = Path(__file__).with_name("map.json")

def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def load_snapshot():
    return json.loads(MAP_PATH.read_text(encoding="utf-8"), object_pairs_hook=unique_object)


def instant(value):
    if not isinstance(value, str):
        raise ValueError("Timestamp text required")
    parsed = datetime.fromisoformat(value)
    if parsed.utcoffset() is None:
        raise ValueError("Explicit offset required")
    return parsed.astimezone(timezone.utc)


def validate_scope(snapshot, policy, map_id, as_of):
    cutoff = instant(as_of)
    for evidence in (snapshot, policy):
        if evidence["map_id"] != map_id or instant(evidence["issued_at"]) > cutoff:
            raise ValueError("Evidence is out of scope or newer than review time")


def identifier(value):
    if not isinstance(value, str) or re.fullmatch(r"[A-Za-z0-9_-]{1,32}", value) is None:
        raise ValueError("Expected ASCII identifier up to 32 characters")
    return value


def positive_integer(value, maximum):
    if type(value) is not int or not 1 <= value <= maximum:
        raise ValueError("Expected bounded positive integer")
    return value


def assess(snapshot, policy, as_of):
    validate_scope(snapshot, policy, policy["map_id"], as_of)
    age = (instant(as_of) - instant(snapshot["issued_at"])).total_seconds()
    if age > positive_integer(policy["max_age_seconds"],3600) or snapshot["declared_complete"] is not True:
        raise ValueError("Fresh complete map required")
    if snapshot["unit"] != "m" or policy["unit"] != "m":
        raise ValueError("Integer metre contract required")
    nodes = snapshot["nodes"]
    if not isinstance(nodes,list) or not 1 <= len(nodes) <= 12:
        raise ValueError("Expected 1 to 12 nodes")
    checked = [identifier(node) for node in nodes]
    if len(set(checked)) != len(checked):
        raise ValueError("Duplicate node ID")
    graph = {node: [] for node in checked}
    start, goal = identifier(policy["start"]), identifier(policy["goal"])
    if start not in graph or goal not in graph:
        raise ValueError("Endpoints must be declared nodes")
    edges = snapshot["edges"]
    if not isinstance(edges,list) or len(edges) > 40:
        raise ValueError("Expected at most 40 directed edges")
    seen, closed = set(), []
    for edge in edges:
        if not isinstance(edge,dict) or set(edge) != {"from","to","distance_m","open"}:
            raise ValueError("Invalid edge fields")
        left, right = identifier(edge["from"]), identifier(edge["to"])
        if left not in graph or right not in graph or left == right or (left,right) in seen:
            raise ValueError("Unknown endpoint, self edge or duplicate directed edge")
        seen.add((left,right))
        distance = positive_integer(edge["distance_m"],1000)
        if type(edge["open"]) is not bool:
            raise ValueError("Explicit boolean aisle state required")
        if edge["open"]:
            graph[left].append((right,distance))
        else:
            closed.append({"from":left,"to":right})
    for neighbours in graph.values():
        neighbours.sort()
    best, parent = {start:0}, {}
    frontier, settled, trace = [(0,start)], set(), []
    while frontier:
        distance, node = heapq.heappop(frontier)
        if node in settled or distance != best[node]:
            continue
        settled.add(node)
        trace.append({"node":node,"distance_m":distance})
        if node == goal:
            break
        for target, length in graph[node]:
            candidate = distance + length
            if candidate < best.get(target,float("inf")):
                best[target], parent[target] = candidate, node
                heapq.heappush(frontier,(candidate,target))
    path = []
    if goal in settled:
        node = goal
        while True:
            path.append(node)
            if node == start:
                break
            node = parent[node]
        path.reverse()
    return {"source":"route-result-demo-01","inputs":[snapshot["source"],policy["source"]],
            "map_id":policy["map_id"],"start":start,"goal":goal,"unit":"m",
            "status":"proposal" if path else "unreachable","path":path,
            "distance_m":best[goal] if path else None,
            "closed_edges":sorted(closed,key=lambda row:(row["from"],row["to"])),
            "settled":trace,"movement_actions_executed":False}


TOOL_DESCRIPTIONS = {
    "lookup_policy": "Read fixed start/goal, unit and map freshness contract",
    "lookup_map": "Read the bounded synthetic directed map with explicit aisle states",
    "find_route": "Find a minimum-distance route on open edges or explicitly report unreachable",
}

def tools():
    return [{"type": "function", "function": {"name": name, "description": description,
             "parameters": {"type": "object", "properties": {"map_id": {"type": "string"}},
                            "required": ["map_id"], "additionalProperties": False}}}
            for name, description in TOOL_DESCRIPTIONS.items()]


def execute(name, arguments, map_id, as_of, snapshot):
    if name not in TOOL_DESCRIPTIONS or arguments != {"map_id": map_id}:
        raise ValueError("Invalid tool or map argument")
    validate_scope(snapshot, POLICY, map_id, as_of)
    if name == "lookup_policy":
        return [POLICY]
    if name == "lookup_map":
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
