import unittest
from agent import match, ORDERS, RECEIPTS, INVOICES, execute


class MatchTests(unittest.TestCase):
    def test_partial_receipt(self):
        result = match(ORDERS["INV-DEMO-01"], RECEIPTS["INV-DEMO-01"], INVOICES["INV-DEMO-01"])
        self.assertIn("invoiced_above_received", result["issues"])
        self.assertEqual(result["calculated_line_total"], "125.00")
        self.assertFalse(result["payment_authorized"])

    def test_wrong_total(self):
        invoice = {**INVOICES["INV-DEMO-01"], "line_total": "124.00"}
        self.assertIn("line_total_mismatch", match(ORDERS["INV-DEMO-01"], RECEIPTS["INV-DEMO-01"], invoice)["issues"])

    def test_scope(self):
        with self.assertRaises(ValueError):
            execute("lookup_order", {"invoice_id": "other"}, "INV-DEMO-01")


if __name__ == "__main__":
    unittest.main()
