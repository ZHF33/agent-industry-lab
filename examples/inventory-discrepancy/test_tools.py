"""Tool contract tests; invocation is optional and documented separately."""
import unittest
from agent import execute


class ToolTests(unittest.TestCase):
    def test_difference(self):
        result = execute("calculate_difference", {"sku": "SKU-DEMO-01"}, "SKU-DEMO-01")
        self.assertEqual(result[0]["difference"], -6)
        self.assertEqual(len(result[0]["inputs"]), 2)

    def test_unknown_item(self):
        self.assertEqual(execute("lookup_stock", {"sku": "missing"}, "missing"), [])

    def test_cross_item(self):
        with self.assertRaises(ValueError):
            execute("lookup_stock", {"sku": "other"}, "SKU-DEMO-01")

    def test_unknown_tool(self):
        with self.assertRaises(ValueError):
            execute("adjust_stock", {"sku": "SKU-DEMO-01"}, "SKU-DEMO-01")


if __name__ == "__main__":
    unittest.main()
