"""Synthetic boundary tests; no model or storage calls."""
from copy import deepcopy
import unittest
from agent import OBJECTS, assess, execute

AS_OF = "2026-10-25T12:00:30+00:00"

class ToolTests(unittest.TestCase):
    def record(self):
        return deepcopy(OBJECTS["OBJECT-DEMO-01"])

    def test_marker_and_older_restriction(self):
        report = assess(self.record(), AS_OF)
        self.assertEqual(report["current_kind_from_snapshot"], "delete_marker")
        self.assertEqual(report["version_findings"][0]["status"], "restriction_recorded")
        self.assertFalse(report["deletion_authorized"])

    def test_expiry_is_not_permission(self):
        record = self.record()
        record["retention"]["versions"][0]["retain_until"] = "2026-10-01T00:00:00+00:00"
        result = assess(record, AS_OF)
        self.assertEqual(result["version_findings"][0]["status"], "no_active_restriction_recorded")
        self.assertFalse(result["deletion_authorized"])

    def test_hold_without_date(self):
        record = self.record()
        record["retention"]["versions"][0].update(retain_until=None, legal_hold=True)
        self.assertEqual(assess(record, AS_OF)["version_findings"][0]["status"], "restriction_recorded")

    def test_stale(self):
        self.assertEqual(assess(self.record(), "2026-10-25T12:02:00+00:00")["version_findings"][0]["status"], "insufficient_evidence")

    def test_incomplete(self):
        record = self.record(); record["inventory"]["complete"] = False
        self.assertEqual(assess(record, AS_OF)["current_kind_from_snapshot"], "unknown")

    def test_missing_metadata(self):
        record = self.record(); record["retention"]["versions"] = []
        self.assertEqual(assess(record, AS_OF)["version_findings"][0]["status"], "missing_retention_evidence")

    def test_unknown_version(self):
        record = self.record(); record["retention"]["versions"][0]["version_id"] = "other"
        with self.assertRaises(ValueError): assess(record, AS_OF)

    def test_duplicate_version(self):
        record = self.record(); record["inventory"]["versions"].append(record["inventory"]["versions"][0])
        with self.assertRaises(ValueError): assess(record, AS_OF)

    def test_scope(self):
        with self.assertRaises(ValueError): execute("lookup_retention", {"object_id": "OTHER"}, "OBJECT-DEMO-01", AS_OF)

    def test_naive_time(self):
        with self.assertRaises(ValueError): assess(self.record(), "2026-10-25T12:00:30")

    def test_future_snapshot(self):
        with self.assertRaises(ValueError): assess(self.record(), "2026-10-25T11:59:00+00:00")

    def test_identity_mismatch(self):
        record = self.record(); record["retention"]["object_id"] = "OTHER"
        self.assertEqual(assess(record, AS_OF)["version_findings"][0]["status"], "insufficient_evidence")

if __name__ == "__main__": unittest.main()
