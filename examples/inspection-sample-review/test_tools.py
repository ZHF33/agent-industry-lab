"""Manual offline checks; expected invariants, not model certification."""
import copy
import hashlib
import unittest
from agent import POLICY, assess, execute, load_snapshot, score, unique_object

AS_OF = "2026-11-23T13:00:00Z"

class ToolTests(unittest.TestCase):
    def test_strata_and_shortage(self):
        result = assess(load_snapshot(), POLICY, AS_OF)
        self.assertEqual(result["selected_count"], 3)
        self.assertEqual(result["requested_count"], 4)
        self.assertEqual(result["status"], "short_population")
        a, b = result["strata"]
        self.assertEqual((a["available"],len(a["selected"]),a["shortage"]), (3,2,0))
        self.assertEqual((b["selected"][0]["unit_id"], b["shortage"]), ("UNIT-04",1))
        self.assertFalse(result["quality_acceptance"])

    def test_input_order_does_not_change_plan(self):
        snapshot = load_snapshot()
        expected = assess(snapshot, POLICY, AS_OF)
        snapshot["units"].reverse()
        self.assertEqual(assess(snapshot, POLICY, AS_OF), expected)

    def test_reject_duplicates_and_unknown_strata(self):
        for row in ({"unit_id":"UNIT-01","stratum":"B"}, {"unit_id":"NEW","stratum":"C"}):
            snapshot = load_snapshot()
            snapshot["units"].append(row)
            with self.assertRaises(ValueError):
                assess(snapshot, POLICY, AS_OF)

    def test_empty_stratum_and_boolean_quota(self):
        snapshot = load_snapshot()
        snapshot["units"] = []
        self.assertEqual(assess(snapshot, POLICY, AS_OF)["selected_count"], 0)
        policy = copy.deepcopy(POLICY)
        policy["quotas"]["A"] = True
        with self.assertRaises(ValueError):
            assess(snapshot, policy, AS_OF)

    def test_protocol_bytes(self):
        expected = hashlib.sha256(b'["seed","batch","A","unit"]').hexdigest()
        self.assertEqual(score("seed","batch","A","unit"), expected)
        self.assertNotEqual(score("ab","c","A","unit"), score("a","bc","A","unit"))

    def test_scope_and_future(self):
        with self.assertRaises(ValueError):
            execute("plan_sample", {"batch_id":"OTHER"}, "BATCH-DEMO-A", AS_OF, load_snapshot())
        with self.assertRaises(ValueError):
            assess(load_snapshot(), POLICY, "2026-11-22T13:00:00Z")
        with self.assertRaises(ValueError):
            unique_object([("unit_id","a"),("unit_id","b")])

if __name__ == "__main__":
    unittest.main()
