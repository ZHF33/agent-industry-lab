"""Acceptance source; no broker, worker, API or model execution."""
import copy
import unittest
from agent import QUEUES, assess, execute


class QueueTests(unittest.TestCase):
    def record(self):
        return copy.deepcopy(QUEUES["QUEUE-DEMO-01"])

    def test_sample(self):
        r = assess(self.record(), "2026-10-22T12:55:00+00:00")
        self.assertEqual((r["total_start"], r["total_end"]), (120, 300))
        self.assertTrue(r["counters_consistent"])
        self.assertEqual(r["published_per_second"], "2")
        self.assertEqual(r["acked_per_second"], "1.4")
        self.assertEqual(r["zero_arrival_drain_seconds_estimate"], "214.29")
        self.assertIn("arrival_rate_exceeds_ack_rate", r["warnings"])
        self.assertFalse(r["actions_executed"])

    def test_mismatch_disables_estimate(self):
        r = self.record()
        r["ready_end"] += 1
        result = assess(r, "2026-10-22T12:55:00+00:00")
        self.assertFalse(result["counters_consistent"])
        self.assertIsNone(result["zero_arrival_drain_seconds_estimate"])

    def test_stale(self):
        result = assess(self.record(), "2026-10-22T12:57:01+00:00")
        self.assertFalse(result["snapshot_fresh"])
        self.assertIsNone(result["zero_arrival_drain_seconds_estimate"])

    def test_zero_ack(self):
        r = self.record()
        r.update(acked=0, ready_end=670, unacked_end=50)
        result = assess(r, "2026-10-22T12:55:00+00:00")
        self.assertTrue(result["counters_consistent"])
        self.assertIsNone(result["zero_arrival_drain_seconds_estimate"])

    def test_no_consumers(self):
        r = self.record()
        r["consumers"] = 0
        self.assertIn("no_consumers_recorded", assess(r, "2026-10-22T12:55:00+00:00")["warnings"])

    def test_bool_counter_rejected(self):
        r = self.record()
        r["acked"] = True
        with self.assertRaises(ValueError):
            assess(r, "2026-10-22T12:55:00+00:00")

    def test_future(self):
        with self.assertRaises(ValueError):
            assess(self.record(), "2026-10-22T12:54:59+00:00")

    def test_missing_timezone(self):
        with self.assertRaises(ValueError):
            assess(self.record(), "2026-10-22T12:55:00")

    def test_scope(self):
        with self.assertRaises(ValueError):
            execute("lookup_queue", {"queue_id": "OTHER"}, "QUEUE-DEMO-01", "2026-10-22T12:55:00+00:00")

    def test_zero_window(self):
        r = self.record()
        r["window_start"] = r["window_end"]
        with self.assertRaises(ValueError):
            assess(r, "2026-10-22T12:55:00+00:00")


if __name__ == "__main__":
    unittest.main()
