"""Synthetic acceptance source; does not read databases or contact a model."""
import copy
import unittest
from agent import SYSTEMS, assess, execute


class RecoveryTests(unittest.TestCase):
    def record(self):
        return copy.deepcopy(SYSTEMS["RECOVERY-DEMO-01"])

    def test_sample(self):
        result = assess(self.record(), "2026-10-21T13:04:00+00:00")
        self.assertEqual(result["recorded_point_lag_seconds"], 840)
        self.assertEqual(result["recorded_service_ready_seconds"], 1320)
        self.assertEqual(result["rpo_evidence"], "recorded_point_within_target")
        self.assertFalse(result["drill_fresh"])
        self.assertIn("latest_backup_not_tested_by_recorded_drill", result["gaps"])
        self.assertEqual(result["actual_recoverability"], "unknown")
        self.assertFalse(result["actions_executed"])

    def test_rpo_boundary(self):
        self.assertEqual(assess(self.record(), "2026-10-21T13:05:00+00:00")
                         ["rpo_evidence"], "recorded_point_within_target")
        self.assertEqual(assess(self.record(), "2026-10-21T13:05:00.1+00:00")
                         ["rpo_evidence"], "recorded_point_exceeds_target")

    def test_same_instant(self):
        self.assertEqual(assess(self.record(), "2026-10-21T09:04:00-04:00")
                         ["recorded_point_lag_seconds"], 840)

    def test_stale_manifest(self):
        self.assertEqual(assess(self.record(), "2026-10-21T14:05:00+00:00")
                         ["rpo_evidence"], "insufficient_evidence")

    def test_missing_timezone(self):
        with self.assertRaises(ValueError):
            assess(self.record(), "2026-10-21T13:04:00")

    def test_future_evidence(self):
        with self.assertRaises(ValueError):
            assess(self.record(), "2026-10-21T13:03:00+00:00")

    def test_inconsistent_timeline(self):
        record = self.record()
        record["completed_at"] = "2026-10-21T12:40:00+00:00"
        with self.assertRaises(ValueError):
            assess(record, "2026-10-21T13:04:00+00:00")

    def test_scope(self):
        with self.assertRaises(ValueError):
            execute("lookup_backup", {"system_id": "OTHER"}, "RECOVERY-DEMO-01",
                    "2026-10-21T13:04:00+00:00")

    def test_failed_backup(self):
        record = self.record()
        record["status"] = "failed"
        self.assertEqual(assess(record, "2026-10-21T13:04:00+00:00")
                         ["rpo_evidence"], "insufficient_evidence")

    def test_failed_drill(self):
        record = self.record()
        record["drill"]["status"] = "failed"
        self.assertEqual(assess(record, "2026-10-21T13:04:00+00:00")
                         ["historical_rto_evidence"], "insufficient_evidence")


if __name__ == "__main__":
    unittest.main()
