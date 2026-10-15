import unittest
from agent import assess, FEEDS, READINGS, execute


class QualityTests(unittest.TestCase):
    def test_quality(self):
        result = assess(FEEDS["FEED-DEMO-01"], READINGS["FEED-DEMO-01"])
        self.assertEqual(result["latest_age_seconds"], 120)
        self.assertEqual({i["type"] for i in result["issues"]}, {"invalid_range", "stale_or_missing"})
        self.assertFalse(result["equipment_failure_confirmed"])

    def test_empty(self):
        self.assertIsNone(assess(FEEDS["FEED-DEMO-01"], [])["latest_age_seconds"])

    def test_scope(self):
        with self.assertRaises(ValueError):
            execute("lookup_feed", {"feed_id": "other"}, "FEED-DEMO-01")


if __name__ == "__main__":
    unittest.main()
