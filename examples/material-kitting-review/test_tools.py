import unittest

from agent import PLAN, POLICY, assess, execute


AS_OF = "2026-11-19T13:15:00Z"


class KitTests(unittest.TestCase):
    def test_zero_stock_is_a_real_constraint(self):
        report = assess(PLAN, POLICY, AS_OF)
        self.assertEqual(report["fulfillable_units"], 0)
        self.assertEqual(report["limiting_materials"], ["SEAL"])
        self.assertEqual([row["shortage"] for row in report["materials"]], [0, 1, 10])

    def test_complete_units_and_target_cap(self):
        stock = {**PLAN, "available": {**PLAN["available"], "SEAL": 10}}
        report = assess(stock, POLICY, AS_OF)
        self.assertEqual(report["fulfillable_units"], 9)
        self.assertEqual(report["limiting_materials"], ["BOLT"])
        stock["available"]["BOLT"] = 20
        self.assertEqual(assess(stock, POLICY, AS_OF)["status"], "sufficient")

    def test_multiple_limiting_materials_and_surplus(self):
        stock = {**PLAN, "available": {"BODY": 10, "BOLT": 18, "SEAL": 9}}
        report = assess(stock, POLICY, AS_OF)
        self.assertEqual(report["limiting_materials"], ["BOLT", "SEAL"])
        stock["available"] = {"BODY": 30, "BOLT": 60, "SEAL": 30}
        report = assess(stock, POLICY, AS_OF)
        self.assertEqual(report["material_capacity"], 30)
        self.assertEqual(report["fulfillable_units"], 10)

    def test_missing_stock_blocks_estimate(self):
        stock = {**PLAN, "available": {"BODY": 10, "BOLT": 19}}
        report = assess(stock, POLICY, AS_OF)
        self.assertIsNone(report["material_capacity"])
        self.assertEqual(report["missing_materials"], ["SEAL"])

    def test_invalid_counts_and_bom(self):
        for value in (True, -1):
            stock = {**PLAN, "available": {**PLAN["available"], "SEAL": value}}
            with self.subTest(value=value), self.assertRaises(ValueError):
                assess(stock, POLICY, AS_OF)
        with self.assertRaises(ValueError):
            assess(PLAN, {**POLICY, "per_unit": {"BODY": 0}}, AS_OF)

    def test_scope_and_future_snapshot(self):
        order = POLICY["order_id"]
        with self.assertRaises(ValueError):
            execute("lookup_stock", {"order_id": "OTHER"}, order, AS_OF)
        with self.assertRaises(ValueError):
            execute("lookup_stock", {"order_id": order}, order, "2026-11-19T12:59:59Z")
