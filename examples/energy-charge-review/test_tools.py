import json
import unittest

from agent import POLICY, assess, execute, load_snapshot, unique_object


AS_OF = "2026-11-18T13:15:00Z"


class EnergyTests(unittest.TestCase):
    def test_round_once_at_total(self):
        snapshot = load_snapshot()
        report = assess(snapshot, POLICY, AS_OF)
        self.assertEqual([row["millicents"] for row in report["rows"]], [26250, 13750])
        self.assertEqual(report["status"], "estimated")
        self.assertEqual(report["total_cents"], 40)
        snapshot["wh_by_slot"] = {"peak": 500, "off_peak": 500}
        # Rounding the two slots independently would give 11 + 6.
        self.assertEqual(assess(snapshot, POLICY, AS_OF)["total_cents"], 16)

    def test_half_cent_and_missing_slot(self):
        snapshot = load_snapshot()
        snapshot["wh_by_slot"] = {"peak": 500, "off_peak": 0}
        self.assertEqual(assess(snapshot, POLICY, AS_OF)["total_cents"], 11)
        del snapshot["wh_by_slot"]["off_peak"]
        report = assess(snapshot, POLICY, AS_OF)
        self.assertEqual(report["missing_slots"], ["off_peak"])
        self.assertIsNone(report["total_cents"])

    def test_invalid_and_duplicate_data(self):
        with self.assertRaisesRegex(ValueError, "Duplicate JSON key"):
            json.loads('{"wh_by_slot":{"peak":0,"peak":1}}', object_pairs_hook=unique_object)
        snapshot = load_snapshot()
        snapshot["wh_by_slot"]["peak"] = True
        with self.assertRaises(ValueError):
            assess(snapshot, POLICY, AS_OF)

    def test_tool_scope_and_evidence_time(self):
        snapshot = load_snapshot()
        meter = snapshot["meter_id"]
        with self.assertRaises(ValueError):
            execute("lookup_readings", {"meter_id": "OTHER"}, meter, AS_OF, snapshot)
        with self.assertRaises(ValueError):
            execute("lookup_readings", {"meter_id": meter}, meter, "2026-11-18T12:59:59Z", snapshot)
