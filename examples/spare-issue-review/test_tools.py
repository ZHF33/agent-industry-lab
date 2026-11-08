"""Deterministic quantity and metadata tests; no model calls."""
import copy
import unittest
from agent import REQUEST, MOVEMENTS, assess, reconcile, execute

class QuantityTests(unittest.TestCase):
    def test_sample(self):
        rows = reconcile(REQUEST["entries"], MOVEMENTS["entries"])
        by_part = {row["part_id"]: row for row in rows}
        self.assertEqual(by_part["BEARING-A"]["net_issued"], 7)
        self.assertEqual(by_part["BEARING-A"]["difference"], -3)
        self.assertEqual(by_part["SEAL-B"]["flags"], ["excess"])
        self.assertIn("return_exceeds_issue", by_part["FILTER-C"]["flags"])
        self.assertEqual(by_part["BEARING-A"]["record_ids"], ["M1", "M2"])

    def test_duplicate_movement_rejected(self):
        with self.assertRaises(ValueError):
            reconcile(REQUEST["entries"], MOVEMENTS["entries"] * 2)

    def test_boolean_fraction_and_bad_unit_rejected(self):
        for changes in ({"quantity": True}, {"quantity": 1.2}, {"quantity": 0}, {"unit": "box"}):
            rows = copy.deepcopy(MOVEMENTS["entries"])
            rows[0].update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                reconcile(REQUEST["entries"], rows)

    def test_duplicate_request_rejected(self):
        with self.assertRaises(ValueError):
            reconcile(REQUEST["entries"] * 2, [])

    def test_unrequested_part(self):
        rows = reconcile([], [MOVEMENTS["entries"][0]])
        self.assertEqual(rows[0]["flags"], ["unrequested_part", "excess"])

    def test_empty_records_keep_shortage(self):
        rows = reconcile(REQUEST["entries"], [])
        self.assertTrue(all(row["flags"] == ["shortage"] for row in rows))

    def test_future_and_naive_time_rejected(self):
        for reference in ("2026-11-08T11:59:59Z", "2026-11-08T12:00:30"):
            with self.subTest(reference=reference), self.assertRaises(ValueError):
                assess(REQUEST, MOVEMENTS, reference)

    def test_age_boundary_and_revision(self):
        report = assess(REQUEST, MOVEMENTS, "2026-11-08T12:01:00Z")
        self.assertEqual(report["limitations"], [])
        evidence = copy.deepcopy(MOVEMENTS)
        evidence["revision"] = 2
        report = assess(REQUEST, evidence, "2026-11-08T12:01:01Z")
        self.assertEqual(report["limitations"], ["revision_mismatch", "stale_evidence"])
        self.assertFalse(report["stock_release_authorized"])

    def test_scope(self):
        with self.assertRaises(ValueError):
            execute("lookup_request", {"request_id": "OTHER"}, "REQ-DEMO-A", "2026-11-08T12:00:30Z")

    def test_row_limit(self):
        with self.assertRaises(ValueError):
            reconcile(REQUEST["entries"] * 34, [])

if __name__ == "__main__":
    unittest.main()
