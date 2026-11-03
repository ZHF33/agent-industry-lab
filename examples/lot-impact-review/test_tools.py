"""Manual acceptance sources; not executed on delivery, no real-model calls."""
import copy
import unittest
from agent import SNAPSHOTS, trace_downstream, assess, execute

AS_OF = "2026-11-03T12:00:30+00:00"


class ToolTests(unittest.TestCase):
    def fixture(self): return copy.deepcopy(SNAPSHOTS["LOT-RAW-A"])

    def test_sample_candidates(self):
        r=assess(self.fixture(), AS_OF)
        self.assertEqual({x["lot_id"] for x in r["candidate_lots"]}, {"LOT-MIX-B", "LOT-PACK-C", "LOT-SHIP-D"})
        self.assertEqual(r["visited_node_count"], 4)
        self.assertEqual(len(r["frontier_edges"]), 1)
        self.assertFalse(r["recall_authorized"])

    def test_direction_does_not_reach_other_input(self):
        r=assess(self.fixture(), AS_OF)
        self.assertNotIn("LOT-RAW-X", {x["lot_id"] for x in r["candidate_lots"]})

    def test_evidence_path(self):
        rows=assess(self.fixture(), AS_OF)["candidate_lots"]
        row=next(x for x in rows if x["lot_id"]=="LOT-PACK-C")
        self.assertEqual(row["path_sources"], ["edge-demo-01", "edge-demo-03"])

    def test_zero_budget(self):
        d=self.fixture()["links"]
        r=trace_downstream(d["nodes"],d["edges"],"LOT-RAW-A",0)
        self.assertEqual(r["candidate_lots"],[])
        self.assertTrue(r["within_snapshot_truncated"])

    def test_larger_budget(self):
        d=self.fixture()["links"]
        r=trace_downstream(d["nodes"],d["edges"],"LOT-RAW-A",4)
        self.assertEqual(len(r["candidate_lots"]),4)
        self.assertFalse(r["within_snapshot_truncated"])

    def test_cycle_terminates(self):
        r=trace_downstream(["A","B"],[{"source":"ab","from":"A","to":"B"},{"source":"ba","from":"B","to":"A"}],"A",3)
        self.assertEqual(r["visited_node_count"],2)
        self.assertEqual(len(r["candidate_lots"]),1)

    def test_missing_endpoint_rejected(self):
        with self.assertRaises(ValueError): trace_downstream(["A"],[{"source":"ab","from":"A","to":"B"}],"A",2)

    def test_duplicate_edges_rejected(self):
        e={"source":"ab","from":"A","to":"B"}
        with self.assertRaises(ValueError): trace_downstream(["A","B"],[e,e],"A",2)

    def test_invalid_budget(self):
        with self.assertRaises(ValueError): trace_downstream(["A"],[],"A",True)

    def test_coverage_declaration(self):
        d=self.fixture(); d["links"]["declared_complete"]=False
        self.assertIn("source_declares_incomplete",assess(d,AS_OF)["limitations"])

    def test_stale_future(self):
        self.assertIn("stale_snapshot",assess(self.fixture(),"2026-11-03T12:01:01+00:00")["limitations"])
        with self.assertRaises(ValueError): assess(self.fixture(),"2026-11-03T11:59:59+00:00")

    def test_wrong_seed(self):
        d=self.fixture(); d["links"]["seed_lot_id"]="OTHER"
        with self.assertRaises(ValueError): assess(d,AS_OF)

    def test_scoped_allowlist(self):
        for name,args in [("recall",{"lot_id":"LOT-RAW-A"}),("lookup_links",{"lot_id":"OTHER"}),
                          ("lookup_links",{"lot_id":"LOT-RAW-A","max_hops":10})]:
            with self.assertRaises(ValueError): execute(name,args,"LOT-RAW-A",AS_OF)


if __name__ == "__main__": unittest.main()
