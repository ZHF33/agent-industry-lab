import copy
import unittest
from agent import CHECKLIST, OBSERVATIONS, assess, execute, reconcile


class ReconciliationTests(unittest.TestCase):
    def test_fixture(self):
        report = assess(CHECKLIST, OBSERVATIONS, "2026-11-07T12:00:30Z")
        self.assertEqual(report["matched_pair_count"], 2)
        self.assertEqual(report["missing"], [{"device_id": "PUMP-A", "check_id": "TEMP", "records": []}])
        self.assertEqual(report["unexpected"][0]["device_id"], "PUMP-C")
        self.assertEqual([r["record_id"] for r in report["conflicts"][0]["records"]], ["R1", "R2"])
        self.assertFalse(report["release_authorized"])

    def test_multiple_agreement(self):
        rows = copy.deepcopy(OBSERVATIONS["entries"])
        rows[1]["result"] = "pass"
        report = reconcile(CHECKLIST["entries"], rows)
        self.assertEqual(len(report["multiple"]), 1)
        self.assertEqual(report["conflicts"], [])

    def test_empty_observations(self):
        self.assertEqual(len(reconcile(CHECKLIST["entries"], [])["missing"]), 3)

    def test_duplicate_record(self):
        rows = OBSERVATIONS["entries"]
        with self.assertRaises(ValueError):
            reconcile(CHECKLIST["entries"], rows + [rows[0]])

    def test_duplicate_plan_pair(self):
        rows = CHECKLIST["entries"]
        with self.assertRaises(ValueError):
            reconcile(rows + [rows[0]], [])

    def test_invalid_result(self):
        with self.assertRaises(ValueError):
            reconcile([], [{**OBSERVATIONS["entries"][0], "result": "approved"}])

    def test_revision_and_stale(self):
        report = assess(CHECKLIST, {**OBSERVATIONS, "revision": 1}, "2026-11-07T12:01:01Z")
        self.assertEqual(report["limitations"], ["revision_mismatch", "stale_evidence"])

    def test_future(self):
        with self.assertRaises(ValueError):
            assess(CHECKLIST, OBSERVATIONS, "2026-11-07T11:59:59Z")

    def test_tool_scope(self):
        with self.assertRaises(ValueError):
            execute("lookup_observations", {"checklist_id": "OTHER"}, "CHECK-DEMO-A", "2026-11-07T12:00:30Z")
