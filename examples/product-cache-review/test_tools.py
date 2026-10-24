"""Synthetic acceptance source; no Redis/model/service execution."""
import copy
import unittest
from agent import PRODUCTS, assess, execute


class CacheTests(unittest.TestCase):
    def record(self):
        return copy.deepcopy(PRODUCTS["PRODUCT-DEMO-01"])

    def test_positive_ttl_can_be_stale_business_data(self):
        r = assess(self.record(), "2026-10-24T11:05:00+00:00")
        self.assertEqual(r["projected_remaining_ttl_seconds"], 180)
        self.assertFalse(r["origin_version_match"])
        self.assertEqual(r["cache_minus_origin_price"], "-0.50")
        self.assertFalse(r["invalidation_executed"])

    def test_missing(self):
        r = self.record(); r["cache"]["ttl_seconds_at_observation"] = -2
        result = assess(r, "2026-10-24T11:05:00+00:00")
        self.assertEqual(result["cache_state_from_snapshot"], "missing_at_observation")
        self.assertIsNone(result["cache_minus_origin_price"])

    def test_no_expiry(self):
        r = self.record(); r["cache"]["ttl_seconds_at_observation"] = -1
        self.assertIn("no_expiry_recorded", assess(r, "2026-10-24T11:05:00+00:00")["warnings"])

    def test_zero_ttl(self):
        r = self.record(); r["cache"]["ttl_seconds_at_observation"] = 0
        self.assertEqual(assess(r, "2026-10-24T11:05:00+00:00")["cache_state_from_snapshot"], "elapsed_ttl_projection")

    def test_stale_evidence(self):
        r = assess(self.record(), "2026-10-24T11:06:01+00:00")
        self.assertFalse(r["evidence_fresh"])
        self.assertIsNone(r["cache_minus_origin_price"])

    def test_currency_mismatch(self):
        r = self.record(); r["cache"]["currency"] = "EUR"
        self.assertIsNone(assess(r, "2026-10-24T11:05:00+00:00")["cache_minus_origin_price"])

    def test_identity_mismatch(self):
        r = self.record(); r["cache"]["product_id"] = "OTHER"
        self.assertIsNone(assess(r, "2026-10-24T11:05:00+00:00")["origin_version_match"])

    def test_invalid_money(self):
        r = self.record(); r["cache"]["price"] = "NaN"
        with self.assertRaises(ValueError):
            assess(r, "2026-10-24T11:05:00+00:00")

    def test_time(self):
        for value in ["2026-10-24T11:05:00", "2026-10-24T11:04:00+00:00"]:
            with self.assertRaises(ValueError):
                assess(self.record(), value)

    def test_scope(self):
        with self.assertRaises(ValueError):
            execute("lookup_origin", {"product_id": "OTHER"}, "PRODUCT-DEMO-01", "2026-10-24T11:05:00+00:00")


if __name__ == "__main__":
    unittest.main()
