import unittest

from agent import PLAN, POLICY, assess, execute


AS_OF = "2026-11-17T13:15:00Z"


class DockTests(unittest.TestCase):
    def test_mixed_offsets_and_touching_boundaries(self):
        report = assess(PLAN, POLICY, AS_OF)
        self.assertEqual(report["peak"], 3)
        self.assertEqual(report["status"], "capacity_conflict")
        self.assertEqual(report["conflicts"], [{
            "start": "2026-11-18T09:30:00+00:00",
            "end": "2026-11-18T10:00:00+00:00",
            "booking_ids": ["A", "B", "C"],
            "required": 3,
            "shortage": 1,
        }])

    def test_capacity_equal_to_peak(self):
        report = assess(PLAN, {**POLICY, "capacity": 3}, AS_OF)
        self.assertEqual(report["status"], "within_capacity")
        self.assertEqual(report["conflicts"], [])

    def test_no_bookings(self):
        report = assess({**PLAN, "bookings": []}, POLICY, AS_OF)
        self.assertEqual(report["peak"], 0)

    def test_invalid_evidence(self):
        first = PLAN["bookings"][0]
        for rows in ([first, first], [{**first, "end": first["start"]}],
                     [{**first, "start": "2026-11-18T09:00:00"}]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                assess({**PLAN, "bookings": rows}, POLICY, AS_OF)

    def test_scope_and_evidence_time(self):
        pool = PLAN["pool_id"]
        with self.assertRaises(ValueError):
            execute("lookup_plan", {"pool_id": "OTHER"}, pool, AS_OF)
        with self.assertRaises(ValueError):
            execute("lookup_plan", {"pool_id": pool}, pool, "2026-11-17T12:44:59Z")
