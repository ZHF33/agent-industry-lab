"""Synthetic directed lot lineage, no recall, stock change or notification."""
import json
import os
import re
import urllib.request
from collections import deque
from datetime import datetime, timezone

SNAPSHOTS = {"LOT-RAW-A": {
    "lot": {"source": "lot-demo-01", "lot_id": "LOT-RAW-A", "kind": "synthetic_industrial_input",
            "observed_at": "2026-11-03T12:00:00+00:00"},
    "links": {"source": "lineage-demo-01", "seed_lot_id": "LOT-RAW-A", "declared_complete": True,
              "observed_at": "2026-11-03T12:00:00+00:00",
              "nodes": ["LOT-RAW-A", "LOT-RAW-X", "LOT-MIX-B", "LOT-PACK-C", "LOT-SHIP-D", "LOT-REPACK-E"],
              "edges": [
                  {"source": "edge-demo-01", "from": "LOT-RAW-A", "to": "LOT-MIX-B"},
                  {"source": "edge-demo-02", "from": "LOT-RAW-X", "to": "LOT-MIX-B"},
                  {"source": "edge-demo-03", "from": "LOT-MIX-B", "to": "LOT-PACK-C"},
                  {"source": "edge-demo-04", "from": "LOT-PACK-C", "to": "LOT-SHIP-D"},
                  {"source": "edge-demo-05", "from": "LOT-SHIP-D", "to": "LOT-REPACK-E"}]}
}}
POLICY = {"source": "lineage-policy-demo-01", "max_hops": 3, "max_age_seconds": 60,
          "scope": "Synthetic input-to-output links, not defect proof or recall authorization."}


def instant(value):
    if not isinstance(value, str): raise ValueError("Timestamp text required")
    result = datetime.fromisoformat(value)
    if result.tzinfo is None or result.utcoffset() is None: raise ValueError("Timezone required")
    return result.astimezone(timezone.utc)


def trace_downstream(nodes, edges, seed, max_hops):
    if type(max_hops) is not int or not 0 <= max_hops <= 10: raise ValueError("Invalid hop budget")
    if not isinstance(nodes, list) or not 1 <= len(nodes) <= 100: raise ValueError("Need 1–100 nodes")
    if any(not isinstance(n, str) or not re.fullmatch(r"[A-Z0-9-]{1,80}", n) for n in nodes):
        raise ValueError("Invalid node ID")
    if len(set(nodes)) != len(nodes) or seed not in nodes: raise ValueError("Unique nodes and known seed required")
    if not isinstance(edges, list) or len(edges) > 200: raise ValueError("At most 200 edges")
    adjacency = {n: [] for n in nodes}; seen_pairs = set(); seen_sources = set()
    for edge in edges:
        if not isinstance(edge, dict) or set(edge) != {"source", "from", "to"}: raise ValueError("Invalid edge fields")
        left, right, source = edge["from"], edge["to"], edge["source"]
        if not isinstance(left, str) or not isinstance(right, str) or left not in adjacency or right not in adjacency:
            raise ValueError("Edge endpoint missing")
        if not isinstance(source, str) or not re.fullmatch(r"[A-Za-z0-9-]{1,100}", source): raise ValueError("Invalid edge source")
        if source in seen_sources or (left, right) in seen_pairs: raise ValueError("Duplicate edge or source")
        seen_sources.add(source); seen_pairs.add((left, right)); adjacency[left].append(edge)
    for links in adjacency.values(): links.sort(key=lambda e: (e["to"], e["source"]))
    queue = deque([seed]); depths = {seed: 0}; paths = {seed: []}; boundary = []
    while queue:
        node = queue.popleft()
        for edge in adjacency[node]:
            target = edge["to"]
            if target in depths: continue
            if depths[node] >= max_hops:
                boundary.append(edge); continue
            depths[target] = depths[node] + 1
            paths[target] = paths[node] + [edge["source"]]
            queue.append(target)
    cut = [e for e in boundary if e["to"] not in depths]
    return {"candidate_lots": [{"lot_id": n, "hops": depths[n], "path_sources": paths[n]}
                               for n in sorted(depths) if n != seed],
            "frontier_edges": cut, "within_snapshot_truncated": bool(cut), "visited_node_count": len(depths)}


def assess(evidence, as_of):
    lot, links = evidence["lot"], evidence["links"]
    if lot["lot_id"] != links["seed_lot_id"]: raise ValueError("Seed mismatch")
    if type(links["declared_complete"]) is not bool: raise ValueError("Boolean coverage declaration required")
    reference = instant(as_of); observed = [instant(x["observed_at"]) for x in (lot, links)]
    if any(t > reference for t in observed): raise ValueError("Future snapshot")
    result = trace_downstream(links["nodes"], links["edges"], lot["lot_id"], POLICY["max_hops"])
    limitations = []
    if any((reference-t).total_seconds() > POLICY["max_age_seconds"] for t in observed): limitations.append("stale_snapshot")
    if not links["declared_complete"]: limitations.append("source_declares_incomplete")
    if result["within_snapshot_truncated"]: limitations.append("hop_budget_truncated")
    return {"source": "impact-assessment-demo-01", "inputs": [lot["source"], links["source"], POLICY["source"]],
            "status": "human_review_required", **result, "limitations": limitations,
            "complete_real_world_scope_verified": False, "defect_proven": False,
            "recall_authorized": False, "actions_executed": False}


def tools():
    descriptions = {"lookup_lot": "Read synthetic seed lot identity and bounded traversal policy",
                    "lookup_links": "Read scoped directed input-to-output lineage snapshot, not live inventory",
                    "assess_impact": "Trace candidate descendants within hop budget, report source paths and cut frontier"}
    return [{"type": "function", "function": {"name": name, "description": description,
             "parameters": {"type": "object", "properties": {"lot_id": {"type": "string"}},
                            "required": ["lot_id"], "additionalProperties": False}}} for name, description in descriptions.items()]


def execute(name, arguments, lot_id, as_of):
    if (name not in {t["function"]["name"] for t in tools()} or not isinstance(arguments, dict)
            or set(arguments) != {"lot_id"} or arguments["lot_id"] != lot_id):
        raise ValueError("Invalid tool or lot scope")
    data = SNAPSHOTS.get(lot_id)
    if data is None: raise ValueError("Unknown synthetic lot")
    if name == "lookup_lot": return [data["lot"], POLICY]
    if name == "lookup_links": return [data["links"]]
    return [assess(data, as_of)]


def chat(messages):
    payload = {"model": os.environ.get("OLLAMA_MODEL", "qwen3:4b"), "messages": messages,
               "tools": tools(), "stream": False, "think": True,
               "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 2500}}
    request = urllib.request.Request("http://127.0.0.1:11434/api/chat", data=json.dumps(payload).encode(),
                                    headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=120) as response: return json.load(response)["message"]
