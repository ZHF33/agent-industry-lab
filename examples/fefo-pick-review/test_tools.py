import copy
import unittest

from agent import POLICY, assess, execute, load_snapshot


AS_OF = "2026-11-21T13:15:00Z"


class PickTests(unittest.TestCase):
    def test_earliest_expiry_and_exclusions(self):
        snapshot = load_snapshot()
        original = copy.deepcopy(snapshot)
        report = assess(snapshot, POLICY, AS_OF)
        self.assertEqual([(p["lot_id"], p["quantity"]) for p in report["picks"]], [("A", 3), ("B", 5)])
        self.assertEqual(report["shortage"], 1)
        self.assertEqual(report["allocated"], 8)
        self.assertEqual([p["lot_id"] for p in report["excluded"]], ["C", "D"])
        self.assertEqual(snapshot, original)

    def test_partial_pick_and_zero_demand(self):
        report = assess(load_snapshot(), {**POLICY, "demand": 4}, AS_OF)
        self.assertEqual([p["quantity"] for p in report["picks"]], [3, 1])
        self.assertEqual(report["status"], "proposed")
        empty = assess(load_snapshot(), {**POLICY, "demand": 0}, AS_OF)
        self.assertEqual(empty["picks"], [])
        self.assertEqual(empty["shortage"], 0)

    def test_expiry_boundary_and_tie_break(self):
        snapshot = load_snapshot()
        snapshot["lots"][2]["expires_at"] = POLICY["use_at"]
        self.assertIn("expires_by_use", assess(snapshot, POLICY, AS_OF)["excluded"][0]["reasons"])
        snapshot["lots"][0]["expires_at"] = snapshot["lots"][1]["expires_at"]
        report = assess(snapshot, {**POLICY, "demand": 1}, AS_OF)
        self.assertEqual(report["picks"][0]["lot_id"], "A")

    def test_bad_evidence_and_scope(self):
        snapshot = load_snapshot()
        snapshot["lots"].append(copy.deepcopy(snapshot["lots"][0]))
        with self.assertRaises(ValueError):
            assess(snapshot, POLICY, AS_OF)
        with self.assertRaises(ValueError):
            execute("lookup_lots", {"request_id": "OTHER"}, POLICY["request_id"], AS_OF, load_snapshot())
        with self.assertRaises(ValueError):
            assess(load_snapshot(), POLICY, "2026-11-21T12:59:59Z")
