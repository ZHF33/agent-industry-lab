import unittest
from agent import SHIPMENT, LOTS, assess, execute

AS_OF = "2026-11-09T14:00:00Z"

class ShelfLifeTests(unittest.TestCase):
    def test_boundary_and_missing(self):
        result = assess(SHIPMENT, LOTS, AS_OF)
        self.assertEqual([row["status"] for row in result["lots"]], [
            "meets_demo_threshold", "below_minimum", "expired_at_arrival",
            "missing_expiry", "missing_lot",
        ])
        self.assertEqual(result["lots"][0]["remaining_seconds"], 86400)
        self.assertEqual(result["lots"][1]["remaining_seconds"], 86399)
        self.assertFalse(result["dispatch_authorized"])

    def test_reject_duplicate_or_unexpected(self):
        for row in (LOTS["entries"][0], {"lot_id": "OTHER", "expires_at": None}):
            with self.subTest(row=row), self.assertRaises(ValueError):
                assess(SHIPMENT, {**LOTS, "entries": LOTS["entries"] + [row]}, AS_OF)

    def test_reject_naive_or_past_arrival(self):
        for when in ("2026-11-09T14:00:00", "2026-11-11T14:00:00Z"):
            with self.subTest(when=when), self.assertRaises(ValueError):
                assess(SHIPMENT, LOTS, when)

    def test_reject_wrong_scope(self):
        with self.assertRaises(ValueError):
            execute("lookup_lots", {"shipment_id": "OTHER"}, SHIPMENT["shipment_id"], AS_OF)
