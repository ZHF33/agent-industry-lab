import unittest

from agent import COUNTS, POLICY, assess, execute


AS_OF = "2026-11-15T13:10:00Z"


class YieldTests(unittest.TestCase):
    def test_pooled_counts_and_inclusive_limit(self):
        report = assess(POLICY, COUNTS, AS_OF)
        self.assertEqual(report["ratio"], {"passed": 95, "inspected": 100})
        self.assertEqual(report["status"], "meets_target")
        self.assertEqual(report["lines"][-1]["status"], "no_inspections")
        tighter = {**POLICY, "minimum_bps": 9501}
        self.assertEqual(assess(tighter, COUNTS, AS_OF)["status"], "below_target")

    def test_missing_does_not_become_zero(self):
        snapshot = {**COUNTS, "rows": {k: v for k, v in COUNTS["rows"].items() if k != "LINE-C"}}
        report = assess(POLICY, snapshot, AS_OF)
        self.assertEqual(report["status"], "missing_lines")
        self.assertIsNone(report["ratio"])

    def test_zero_total(self):
        snapshot = {**COUNTS, "rows": {line: {"passed": 0, "inspected": 0} for line in POLICY["lines"]}}
        report = assess(POLICY, snapshot, AS_OF)
        self.assertEqual(report["status"], "no_inspections")
        self.assertIsNone(report["ratio"])

    def test_impossible_counts(self):
        for passed in (True, -1, 91):
            snapshot = {**COUNTS, "rows": {**COUNTS["rows"], "LINE-A": {"passed": passed, "inspected": 90}}}
            with self.subTest(passed=passed), self.assertRaises(ValueError):
                assess(POLICY, snapshot, AS_OF)

    def test_scope_and_window(self):
        with self.assertRaises(ValueError):
            execute("lookup_counts", {"window_id": "OTHER"}, POLICY["window_id"], AS_OF)
        with self.assertRaises(ValueError):
            execute("lookup_counts", {"window_id": POLICY["window_id"]}, POLICY["window_id"], "2026-11-15T12:59:59Z")
