import unittest
from agent import assess, ORDERS, EVIDENCE, execute


class ReturnTests(unittest.TestCase):
    def test_missing_evidence(self):
        result = assess(ORDERS["RET-DEMO-01"], EVIDENCE["RET-DEMO-01"])
        self.assertEqual(result["elapsed_days"], 13)
        self.assertEqual(result["missing_evidence"], ["photos_received"])
        self.assertFalse(result["refund_authorized"])

    def test_invalid_quantity(self):
        with self.assertRaises(ValueError):
            assess(ORDERS["RET-DEMO-01"], {**EVIDENCE["RET-DEMO-01"], "reported_quantity": 3})

    def test_scope(self):
        with self.assertRaises(ValueError):
            execute("lookup_order", {"return_id": "other"}, "RET-DEMO-01")


if __name__ == "__main__":
    unittest.main()
