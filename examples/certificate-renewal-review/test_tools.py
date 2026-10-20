"""Optional acceptance suite. Does not contact a model or a real endpoint."""
import copy
import unittest
from agent import ASSETS, assess, execute


class CertificateTests(unittest.TestCase):
    def test_boundary_72_hours(self):
        report = assess(ASSETS["CERT-DEMO-01"], "2026-10-20T13:00:00+00:00")
        self.assertEqual(report["snapshot_urgency"], "critical")
        self.assertEqual(report["seconds_to_snapshot_expiry"], 259200)
        self.assertEqual(report["replacement_deployment"], "unconfirmed")
        self.assertEqual(report["current_endpoint_status"], "unknown")

    def test_same_instant_offset(self):
        a = assess(ASSETS["CERT-DEMO-01"], "2026-10-20T09:00:00-04:00")
        self.assertEqual(a["seconds_to_snapshot_expiry"], 259200)

    def test_expiry_and_staleness_separate(self):
        report = assess(ASSETS["CERT-DEMO-01"], "2026-10-23T13:00:00+00:00")
        self.assertEqual(report["snapshot_urgency"], "expired")
        self.assertEqual(report["snapshot_freshness"], "stale_snapshot")
        self.assertFalse(report["actions_executed"])

    def test_future_snapshot(self):
        self.assertEqual(assess(ASSETS["CERT-DEMO-01"], "2026-10-20T12:00:00+00:00")
                         ["snapshot_freshness"], "future_snapshot")

    def test_missing_timezone(self):
        with self.assertRaises(ValueError):
            assess(ASSETS["CERT-DEMO-01"], "2026-10-20T13:00:00")

    def test_scope(self):
        with self.assertRaises(ValueError):
            execute("lookup_certificate", {"asset_id": "OTHER"}, "CERT-DEMO-01",
                    "2026-10-20T13:00:00+00:00")

    def test_invalid_interval(self):
        asset = copy.deepcopy(ASSETS["CERT-DEMO-01"])
        asset["not_before"] = asset["not_after"]
        with self.assertRaises(ValueError):
            assess(asset, "2026-10-20T13:00:00+00:00")


if __name__ == "__main__":
    unittest.main()
