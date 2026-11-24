"""Manual offline checks; no model calls."""
import copy
import unittest
from agent import POLICY, assess, execute, load_snapshot, next_state, unique_object

AS_OF = "2026-11-24T12:33:25Z"

class ToolTests(unittest.TestCase):
    def test_reference_replay(self):
        result = assess(load_snapshot(), POLICY, AS_OF)
        self.assertEqual([r["state"] for r in result["trace"]],
                         ["normal","low","low","low","normal","unknown","low","normal"])
        self.assertEqual((result["low_entries"],result["low_to_normal_recoveries"],result["gap_resets"]),(2,2,1))
        self.assertEqual(result["state_at_review"],"normal")
        self.assertFalse(result["equipment_actions_executed"])

    def test_boundaries_and_memory(self):
        self.assertEqual(next_state("normal",600,600,650),"normal")
        self.assertEqual(next_state("low",600,600,650),"low")
        self.assertEqual(next_state("unknown",625,600,650),"unknown")
        self.assertEqual(next_state("low",650,600,650),"normal")
        self.assertEqual(next_state("unknown",599,600,650),"low")

    def test_gap_equal_limit_keeps_state(self):
        snapshot=load_snapshot()
        snapshot["readings"]=[{"at":"2026-11-24T12:31:20Z","pressure_kpa":625}]
        self.assertEqual(assess(snapshot,POLICY,"2026-11-24T12:33:25Z")["trace"][0]["state"],"normal")
        snapshot["readings"][0]["at"]="2026-11-24T12:31:21Z"
        self.assertEqual(assess(snapshot,POLICY,AS_OF)["trace"][0]["state"],"unknown")

    def test_stale_review_is_unknown(self):
        result=assess(load_snapshot(),POLICY,"2026-11-24T13:00:00Z")
        self.assertEqual(result["last_observed_state"],"normal")
        self.assertEqual(result["state_at_review"],"unknown")

    def test_initial_state_evidence_cannot_come_from_future(self):
        policy=copy.deepcopy(POLICY)
        policy["initial_state_at"]="2026-11-24T12:30:51Z"
        with self.assertRaises(ValueError):
            assess(load_snapshot(),policy,AS_OF)

    def test_review_age_boundary(self):
        snapshot=load_snapshot()
        self.assertEqual(assess(snapshot,POLICY,"2026-11-24T12:33:50Z")["state_at_review"],"normal")
        self.assertEqual(assess(snapshot,POLICY,"2026-11-24T12:33:51Z")["state_at_review"],"unknown")

    def test_reject_bad_order_and_values(self):
        for action in ("reverse","duplicate","boolean","future"):
            snapshot=load_snapshot()
            if action=="reverse":
                snapshot["readings"].reverse()
            elif action=="duplicate":
                snapshot["readings"][1]["at"]=snapshot["readings"][0]["at"]
            elif action=="boolean":
                snapshot["readings"][0]["pressure_kpa"]=True
            else:
                snapshot["readings"][-1]["at"]="2026-11-24T12:33:23Z"
            with self.assertRaises(ValueError):
                assess(snapshot,POLICY,AS_OF)

    def test_scope_unit_thresholds(self):
        with self.assertRaises(ValueError):
            execute("replay_pressure",{"system_id":"OTHER"},"AIR-DEMO-A",AS_OF,load_snapshot())
        snapshot=load_snapshot()
        snapshot["unit"]="bar"
        with self.assertRaises(ValueError):
            assess(snapshot,POLICY,AS_OF)
        policy=copy.deepcopy(POLICY)
        policy["low_below"]=policy["recover_at_or_above"]
        with self.assertRaises(ValueError):
            assess(load_snapshot(),policy,AS_OF)
        with self.assertRaises(ValueError):
            unique_object([("at","a"),("at","b")])

if __name__ == "__main__":
    unittest.main()
