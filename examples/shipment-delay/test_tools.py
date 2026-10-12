import unittest
from agent import assess, execute, utc_time, SHIPMENTS, EVENTS


class ShipmentTests(unittest.TestCase):
    def test_overdue_unconfirmed(self):
        result = assess(SHIPMENTS["SHIP-DEMO-01"], EVENTS["SHIP-DEMO-01"])
        self.assertEqual(result["overdue_minutes"], 60)
        self.assertEqual(result["status"], "past_eta_delivery_unconfirmed")
        self.assertEqual(result["cause"], "unknown")

    def test_timezone_required(self):
        with self.assertRaises(ValueError):
            utc_time("2026-10-12T12:00:00")
        self.assertEqual(utc_time("2026-10-12T08:00:00-04:00"), utc_time("2026-10-12T12:00:00+00:00"))

    def test_future_event(self):
        event = {"source": "future", "occurred_at": "2026-10-12T14:00:00+00:00", "type": "delivered"}
        result = assess(SHIPMENTS["SHIP-DEMO-01"], [event])
        self.assertEqual(result["future_events_ignored"], 1)
        self.assertIsNone(result["last_observed_event"])

    def test_delivery_evidence(self):
        item = {**SHIPMENTS["SHIP-DEMO-01"], "delivered_at": "2026-10-12T12:30:00+00:00"}
        self.assertEqual(assess(item, [])["overdue_minutes"], 30)
        self.assertEqual(assess(item, [])["status"], "delivered_late")

    def test_parameter_boundary(self):
        with self.assertRaises(ValueError):
            execute("lookup_shipment", {"shipment_id": "other"}, "SHIP-DEMO-01")
        self.assertEqual(execute("lookup_shipment", {"shipment_id": "unknown"}, "unknown"), [])


if __name__ == "__main__":
    unittest.main()
