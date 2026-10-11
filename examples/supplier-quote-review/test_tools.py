import unittest
from agent import compare, execute, money, RFQS, QUOTES


class QuoteTests(unittest.TestCase):
    def test_cost_and_delivery(self):
        rows = compare(RFQS["RFQ-DEMO-01"], QUOTES["RFQ-DEMO-01"])
        self.assertEqual(rows[0]["total_before_tax"], "1040.00")
        self.assertEqual(rows[1]["total_before_tax"], "1070.00")
        self.assertFalse(rows[1]["within_lead_time"])

    def test_unknown_cost_and_currency(self):
        rows = compare(RFQS["RFQ-DEMO-01"], QUOTES["RFQ-DEMO-01"])
        self.assertIsNone(rows[2]["total_before_tax"])
        self.assertIn("freight_missing", rows[2]["issues"])
        self.assertIsNone(rows[3]["total_before_tax"])

    def test_boundary(self):
        with self.assertRaises(ValueError):
            execute("lookup_quotes", {"rfq_id": "other"}, "RFQ-DEMO-01")
        self.assertEqual(execute("lookup_request", {"rfq_id": "unknown"}, "unknown"), [])

    def test_invalid_amount(self):
        for value in ["NaN", "Infinity", "-1", 10.2]:
            with self.assertRaises(ValueError):
                money(value)


if __name__ == "__main__":
    unittest.main()
