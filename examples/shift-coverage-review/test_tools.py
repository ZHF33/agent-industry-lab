import unittest
from agent import SHIFT, EVIDENCE, assess, coverage, execute

AS_OF = "2026-11-04T13:00:30Z"


class CoverageTests(unittest.TestCase):
    def test_union_and_gap(self):
        report = assess(SHIFT, EVIDENCE, AS_OF)
        self.assertEqual(report["covered_seconds"], 13200)
        self.assertEqual(report["gap_seconds"], 1200)
        self.assertEqual(report["covered"][0]["sources"], ["record-A", "record-B"])
        self.assertEqual(report["gaps"][0]["start"], "2026-11-04T10:00:00+00:00")
        self.assertFalse(report["actions_executed"])

    def test_empty_and_outside(self):
        row = {"source": "x", "start": "2026-11-04T06:00:00Z", "end": SHIFT["start"]}
        for entries in ([], [row]):
            result = coverage(SHIFT["start"], SHIFT["end"], entries)
            self.assertEqual(result["gap_seconds"], 14400)

    def test_adjacent_and_offset(self):
        entries = [
            {"source": "a", "start": SHIFT["start"], "end": "2026-11-04T05:00:00-05:00"},
            {"source": "b", "start": "2026-11-04T10:00:00Z", "end": SHIFT["end"]},
        ]
        result = coverage(SHIFT["start"], SHIFT["end"], entries)
        self.assertEqual(len(result["covered"]), 1)
        self.assertEqual(result["gaps"], [])

    def test_invalid_intervals(self):
        for row in (
            {"source": "x", "start": SHIFT["end"], "end": SHIFT["start"]},
            {"source": "x", "start": "2026-11-04T08:00:00", "end": SHIFT["end"]},
        ):
            with self.assertRaises(ValueError):
                coverage(SHIFT["start"], SHIFT["end"], [row])

    def test_duplicate_source(self):
        row = EVIDENCE["entries"][0]
        with self.assertRaises(ValueError):
            coverage(SHIFT["start"], SHIFT["end"], [row, row])

    def test_snapshot_limits(self):
        report = assess(SHIFT, {**EVIDENCE, "declared_complete": False}, "2026-11-04T13:01:01Z")
        self.assertEqual(report["limitations"], ["stale_snapshot", "source_declares_incomplete"])
        with self.assertRaises(ValueError):
            assess(SHIFT, EVIDENCE, "2026-11-04T12:59:00Z")

    def test_scope(self):
        with self.assertRaises(ValueError):
            execute("lookup_shift", {"shift_id": "OTHER"}, SHIFT["shift_id"], AS_OF)
