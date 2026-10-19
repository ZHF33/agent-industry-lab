import unittest
from agent import group_events, BATCHES, execute


class AlertTests(unittest.TestCase):
    def test_duplicates(self):
        result = group_events(BATCHES["ALERT-DEMO-01"]["events"])
        self.assertEqual(result["duplicate_deliveries"], 1)
        self.assertEqual(sum(g["unique_events"] for g in result["groups"]), 3)
        self.assertFalse(result["alerts_suppressed"])

    def test_conflicting_identity(self):
        event = BATCHES["ALERT-DEMO-01"]["events"][0]
        result = group_events([event, {**event, "source": "conflict-demo", "severity": "critical"}])
        self.assertEqual(result["conflicting_event_ids"], ["E-1"])
        self.assertEqual(result["groups"], [])

    def test_empty(self):
        self.assertEqual(group_events([])["groups"], [])

    def test_scope(self):
        with self.assertRaises(ValueError):
            execute("lookup_batch", {"batch_id": "other"}, "ALERT-DEMO-01")


if __name__ == "__main__":
    unittest.main()
