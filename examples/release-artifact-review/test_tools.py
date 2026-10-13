import unittest
from agent import verify, execute


class IntegrityTests(unittest.TestCase):
    def test_match(self):
        self.assertTrue(verify({"a": b"demo"}, {"a": b"demo"})["all_expected_match"])

    def test_mismatch(self):
        self.assertEqual(verify({"a": b"demo"}, {"a": b"changed"})["entries"][0]["status"], "mismatch")

    def test_missing_and_unexpected(self):
        rows = verify({"a": b"demo"}, {"b": b"demo"})["entries"]
        self.assertEqual([r["status"] for r in rows], ["missing", "unexpected"])

    def test_empty_not_approved(self):
        self.assertFalse(verify({}, {})["all_expected_match"])
        self.assertFalse(verify({"a": b"demo"}, {"a": b"demo"})["authenticity_verified"])

    def test_tool_scope(self):
        with self.assertRaises(ValueError):
            execute("lookup_manifest", {"release_id": "other"}, "REL-DEMO-01")
        self.assertEqual(execute("lookup_manifest", {"release_id": "unknown"}, "unknown"), [])


if __name__ == "__main__":
    unittest.main()
