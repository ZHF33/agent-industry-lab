import unittest
from agent import COUNTERS, POLICY, assess, execute

AS_OF = "2026-11-14T13:10:00Z"


class ToolLifeTests(unittest.TestCase):
    def test_projection_limits_and_evidence_gaps(self):
        rows = assess(POLICY, COUNTERS, AS_OF)["tools"]
        self.assertEqual([row["status"] for row in rows],
                         ["fits_limit", "exceeds_limit", "counter_regression", "missing_counter"])
        self.assertEqual([row.get("projected") for row in rows], [100, 101, None, None])

    def test_zero_previous_is_present(self):
        snapshot = {**COUNTERS, "previous": {**COUNTERS["previous"], "T1": 0}}
        self.assertEqual(assess(POLICY, snapshot, AS_OF)["tools"][0]["status"], "fits_limit")

    def test_invalid_and_future_evidence(self):
        for value in (True, -1):
            snapshot = {**COUNTERS, "current": {**COUNTERS["current"], "T1": value}}
            with self.subTest(value=value), self.assertRaises(ValueError):
                assess(POLICY, snapshot, AS_OF)
        with self.assertRaises(ValueError):
            assess(POLICY, COUNTERS, "2026-11-14T12:59:59Z")

    def test_tool_scope(self):
        with self.assertRaises(ValueError):
            execute("lookup_counters", {"machine_id": "OTHER"}, POLICY["machine_id"], AS_OF)
