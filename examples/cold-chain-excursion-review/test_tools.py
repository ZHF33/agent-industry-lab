"""Acceptance sources and expectations; no model calls. Run manually."""
import copy
import unittest
from fractions import Fraction
from agent import SHIPMENTS, assess, celsius, execute

AS_OF = "2026-11-01T12:20:00+00:00"


class ToolTests(unittest.TestCase):
    def fixture(self): return copy.deepcopy(SHIPMENTS["SHIP-DEMO-01"])

    def test_unit_conversion(self):
        self.assertEqual(celsius("50", "F"), Fraction(10))
        self.assertEqual(celsius("32", "F"), Fraction(0))

    def test_bad_units_and_numbers(self):
        for value, unit in [("NaN", "C"), ("4", "K"), (4, "C"), ("-274", "C")]:
            with self.subTest(value=value, unit=unit), self.assertRaises(ValueError): celsius(value, unit)

    def test_sample_estimates_and_unknown(self):
        result = assess(self.fixture(), AS_OF)
        self.assertEqual(result["estimated_above_seconds"], 300)
        self.assertEqual(result["estimated_within_seconds"], 300)
        self.assertEqual(result["unknown_seconds"], 600)
        self.assertEqual(len(result["out_of_band_points"]), 2)
        self.assertFalse(result["release_authorized"])

    def test_window_accounting(self):
        r = assess(self.fixture(), AS_OF)
        self.assertEqual(sum(r[k] for k in ["estimated_above_seconds", "estimated_below_seconds", "estimated_within_seconds", "unknown_seconds"]), 1200)

    def test_same_physical_value_in_celsius(self):
        data = self.fixture()
        data["readings"]["samples"][1].update(value="10", unit="C")
        self.assertEqual(assess(data, AS_OF), assess(self.fixture(), AS_OF))

    def test_threshold_is_inclusive(self):
        data = self.fixture()
        for row in data["readings"]["samples"]: row.update(value="8", unit="C")
        r = assess(data, AS_OF)
        self.assertEqual(r["out_of_band_points"], [])
        self.assertEqual(r["unknown_seconds"], 600)

    def test_missing_edges_remain_unknown(self):
        data = self.fixture(); data["readings"]["samples"] = data["readings"]["samples"][1:3]
        self.assertEqual(assess(data, AS_OF)["unknown_seconds"], 900)

    def test_duplicate_or_unsorted_time(self):
        data = self.fixture(); data["readings"]["samples"][1]["at"] = data["readings"]["samples"][0]["at"]
        with self.assertRaisesRegex(ValueError, "order"): assess(data, AS_OF)

    def test_future_window(self):
        with self.assertRaises(ValueError): assess(self.fixture(), "2026-11-01T12:19:00+00:00")

    def test_naive_time(self):
        with self.assertRaises(ValueError): assess(self.fixture(), "2026-11-01T12:20:00")

    def test_stale_evidence(self):
        self.assertIn("stale_snapshot", assess(self.fixture(), "2026-11-01T12:21:01+00:00")["reasons"])

    def test_wrong_identity(self):
        data = self.fixture(); data["readings"]["shipment_id"] = "OTHER"
        with self.assertRaises(ValueError): assess(data, AS_OF)

    def test_scope_and_tool_allowlist(self):
        for name, args in [("release_goods", {"shipment_id": "SHIP-DEMO-01"}),
                           ("lookup_readings", {"shipment_id": "OTHER"}),
                           ("lookup_readings", {"shipment_id": "SHIP-DEMO-01", "url": "forbidden"})]:
            with self.assertRaises(ValueError): execute(name, args, "SHIP-DEMO-01", AS_OF)


if __name__ == "__main__":
    unittest.main()
