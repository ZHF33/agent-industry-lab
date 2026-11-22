import copy
import unittest

from agent import POLICY, assess, execute, load_snapshot


AS_OF = "2026-11-22T13:15:00Z"


class SequenceTests(unittest.TestCase):
    def test_gaps_repeats_and_conflicts(self):
        snapshot = load_snapshot()
        original = copy.deepcopy(snapshot)
        result = assess(snapshot, POLICY, AS_OF)
        self.assertEqual(result["missing_ranges"], [{"first": 101, "last": 101}, {"first": 104, "last": 104}])
        self.assertEqual(result["missing_count"], 2)
        self.assertEqual(result["record_count"], 6)
        self.assertEqual(result["unique_count"], 4)
        self.assertEqual(result["conflicting_sequences"], [103])
        self.assertEqual(result["repeated_sequences"][0]["row_positions"], [2, 3])
        self.assertEqual(snapshot, original)

    def test_reordered_but_covered(self):
        snapshot = load_snapshot()
        snapshot["events"] = [{"sequence": n, "state": "observed"} for n in (105, 100, 102, 101, 104, 103)]
        self.assertEqual(assess(snapshot, POLICY, AS_OF)["status"], "covered")

    def test_huge_empty_window_is_one_range(self):
        policy = {**POLICY, "first": 0, "last": 1_000_000_000_000}
        result = assess({**load_snapshot(), "events": []}, policy, AS_OF)
        self.assertEqual(result["missing_ranges"], [{"first": 0, "last": 1_000_000_000_000}])
        self.assertEqual(result["missing_count"], 1_000_000_000_001)

    def test_outside_window_and_boolean(self):
        for number in (True, 106, -1):
            snapshot = {**load_snapshot(), "events": [{"sequence": number, "state": "observed"}]}
            with self.subTest(number=number), self.assertRaises(ValueError):
                assess(snapshot, POLICY, AS_OF)

    def test_tool_scope_and_snapshot_time(self):
        stream = POLICY["stream_id"]
        with self.assertRaises(ValueError):
            execute("lookup_events", {"stream_id": "OTHER"}, stream, AS_OF, load_snapshot())
        with self.assertRaises(ValueError):
            assess(load_snapshot(), POLICY, "2026-11-22T12:59:59Z")
