import unittest
from agent import EVENTS, POLICY, assess, execute

AS_OF = "2026-11-13T13:10:00Z"


class ClearanceTests(unittest.TestCase):
    def test_sample_includes_end_and_reports_conflict(self):
        report = assess(POLICY, EVENTS, AS_OF)
        rows = {row["point"]: row for row in report["checkpoints"]}
        self.assertEqual(rows["table"]["event_ids"], ["E02"])
        self.assertEqual(rows["feeder"]["state"], "residue")
        self.assertEqual(rows["bin"]["state"], "missing_evidence")
        self.assertEqual(rows["rack"]["state"], "conflict")
        self.assertEqual(rows["rack"]["event_ids"], ["E05", "E06"])
        self.assertEqual(report["excluded_event_ids"], ["E04", "E07"])

    def test_start_included_and_source_order_independent(self):
        self.assertEqual(assess(POLICY, EVENTS, POLICY["started_at"])["checkpoints"][0]["state"], "residue")
        reverse = {**EVENTS, "events": list(reversed(EVENTS["events"]))}
        self.assertEqual(assess(POLICY, EVENTS, AS_OF), assess(POLICY, reverse, AS_OF))

    def test_duplicate_and_scope(self):
        with self.assertRaises(ValueError):
            assess(POLICY, {**EVENTS, "events": EVENTS["events"] * 2}, AS_OF)
        with self.assertRaises(ValueError):
            execute("lookup_events", {"station_id": "OTHER"}, POLICY["station_id"], AS_OF)
