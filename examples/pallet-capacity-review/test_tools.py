import unittest

from agent import PLAN, POLICY, assess, execute


AS_OF = "2026-11-16T13:15:00Z"


class PalletTests(unittest.TestCase):
    def test_missing_capacity_blocks_total(self):
        report = assess(PLAN, POLICY, AS_OF)
        self.assertEqual([row["pallets"] for row in report["groups"]], [2, 1, None])
        self.assertEqual(report["known_group_subtotal"], 3)
        self.assertIsNone(report["total_pallets"])
        self.assertEqual(report["status"], "missing_capacity")

    def test_remainder_and_exact_multiple(self):
        plan = {**PLAN, "cartons_by_group": {"A": 9, "B": 8, "C": 0}}
        report = assess(plan, POLICY, AS_OF)
        self.assertEqual([row.get("remaining_cartons") for row in report["groups"]], [1, 0, None])
        self.assertEqual([row["pallets"] for row in report["groups"]], [2, 1, 0])
        self.assertEqual(report["total_pallets"], 3)

    def test_valid_capacity_completes_estimate(self):
        policy = {**POLICY, "capacity_by_group": {**POLICY["capacity_by_group"], "C": 2}}
        self.assertEqual(assess(PLAN, policy, AS_OF)["total_pallets"], 5)

    def test_invalid_capacity_rejected(self):
        for value in (0, True, -1):
            policy = {**POLICY, "capacity_by_group": {"A": value, "B": 8}}
            with self.subTest(value=value), self.assertRaises(ValueError):
                assess(PLAN, policy, AS_OF)

    def test_wrong_dispatch_and_future_evidence(self):
        dispatch = PLAN["dispatch_id"]
        with self.assertRaises(ValueError):
            execute("lookup_plan", {"dispatch_id": "OTHER"}, dispatch, AS_OF)
        with self.assertRaises(ValueError):
            execute("lookup_plan", {"dispatch_id": dispatch}, dispatch, "2026-11-16T12:59:59Z")
