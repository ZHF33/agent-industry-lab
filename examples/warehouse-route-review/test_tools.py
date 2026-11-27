"""Manual offline route, graph-contract and Dijkstra regression cases."""
import copy
import unittest
from agent import POLICY, assess, execute, load_snapshot

AS_OF="2026-11-27T12:30:30Z"

class ToolTests(unittest.TestCase):
    def test_closed_shortcut(self):
        result=assess(load_snapshot(),POLICY,AS_OF)
        self.assertEqual(result["path"],["ENTRY","B","EXIT"])
        self.assertEqual(result["distance_m"],7)
        self.assertEqual(result["closed_edges"],[{"from":"A","to":"EXIT"}])
        self.assertFalse(result["movement_actions_executed"])

    def test_open_shortcut_and_input_order(self):
        snapshot=load_snapshot()
        snapshot["edges"][1]["open"]=True
        result=assess(snapshot,POLICY,AS_OF)
        self.assertEqual(result["distance_m"],4)
        snapshot["edges"].reverse()
        snapshot["nodes"].reverse()
        self.assertEqual(assess(snapshot,POLICY,AS_OF),result)

    def test_unreachable_direction_and_zero_length_route(self):
        policy=copy.deepcopy(POLICY)
        policy["start"],policy["goal"]="EXIT","ENTRY"
        result=assess(load_snapshot(),policy,AS_OF)
        self.assertEqual((result["status"],result["path"],result["distance_m"]),("unreachable",[],None))
        policy["goal"]="EXIT"
        result=assess(load_snapshot(),policy,AS_OF)
        self.assertEqual((result["path"],result["distance_m"]),(["EXIT"],0))

    def test_goal_must_be_settled_not_first_discovered(self):
        snapshot=load_snapshot()
        snapshot["edges"]=[
            {"from":"ENTRY","to":"EXIT","distance_m":10,"open":True},
            {"from":"ENTRY","to":"A","distance_m":2,"open":True},
            {"from":"A","to":"EXIT","distance_m":2,"open":True},
            {"from":"A","to":"ENTRY","distance_m":1,"open":True}]
        result=assess(snapshot,POLICY,AS_OF)
        self.assertEqual((result["path"],result["distance_m"]),(["ENTRY","A","EXIT"],4))

    def test_bad_edges_rejected(self):
        for kind in ("negative","boolean","flag","duplicate","unknown"):
            snapshot=load_snapshot()
            if kind=="negative":
                snapshot["edges"][0]["distance_m"]=-1
            elif kind=="boolean":
                snapshot["edges"][0]["distance_m"]=True
            elif kind=="flag":
                snapshot["edges"][0]["open"]=1
            elif kind=="duplicate":
                snapshot["edges"].append(dict(snapshot["edges"][0]))
            else:
                snapshot["edges"][0]["to"]="UNKNOWN"
            with self.assertRaises(ValueError):
                assess(snapshot,POLICY,AS_OF)

    def test_scope_and_age(self):
        with self.assertRaises(ValueError):
            execute("find_route",{"map_id":"OTHER"},"MAP-DEMO-A",AS_OF,load_snapshot())
        self.assertEqual(assess(load_snapshot(),POLICY,"2026-11-27T12:31:00Z")["distance_m"],7)
        for time in ("2026-11-27T12:31:01Z","2026-11-27T12:29:59Z"):
            with self.assertRaises(ValueError):
                assess(load_snapshot(),POLICY,time)

if __name__ == "__main__":
    unittest.main()
