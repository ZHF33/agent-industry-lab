"""Reuse bounded synthetic graph traversal; no model, database or business action."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "examples" / "lot-impact-review"))
from agent import trace_downstream

if __name__ == "__main__":
    nodes = ["A", "B", "C", "X"]
    edges = [{"source":"ab", "from":"A", "to":"B"},
             {"source":"bc", "from":"B", "to":"C"},
             {"source":"xb", "from":"X", "to":"B"},
             {"source":"ba", "from":"B", "to":"A"}]
    for hops in [1, 2]:
        r=trace_downstream(nodes, edges, "A", hops)
        print("hops:", hops, "candidates:", [x["lot_id"] for x in r["candidate_lots"]], "cut:", len(r["frontier_edges"]))
