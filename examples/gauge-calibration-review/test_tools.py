import unittest
from agent import POLICY, READINGS, assess, execute

AS_OF = "2026-11-12T13:30:00Z"

class CalibrationTests(unittest.TestCase):
    def test_sample_and_inclusive_boundary(self):
        rows = assess(POLICY, READINGS, AS_OF)["points"]
        self.assertEqual([row["status"] for row in rows],
                         ["inside", "overlaps_limit", "outside", "missing_reading"])
        self.assertEqual([row["interval"] for row in rows[:3]], [[1, 5], [2, 6], [-8, -6]])

    def test_interval_touching_from_outside(self):
        record = {"point": "P10", "measured": 10006, "uncertainty": 1}
        result = assess(POLICY, {**READINGS, "points": [record]}, AS_OF)
        self.assertEqual(result["points"][0]["status"], "overlaps_limit")

    def test_invalid_evidence(self):
        first = READINGS["points"][0]
        for points in ([first, first], [{**first, "uncertainty": -1}],
                       [{**first, "measured": True}], [{**first, "point": "OTHER"}]):
            with self.subTest(points=points), self.assertRaises(ValueError):
                assess(POLICY, {**READINGS, "points": points}, AS_OF)
        with self.assertRaises(ValueError):
            assess(POLICY, {**READINGS, "unit": "mm"}, AS_OF)

    def test_future_and_wrong_scope(self):
        with self.assertRaises(ValueError):
            assess(POLICY, READINGS, "2026-11-12T12:59:59Z")
        with self.assertRaises(ValueError):
            execute("lookup_readings", {"gauge_id": "OTHER"}, POLICY["gauge_id"], AS_OF)
