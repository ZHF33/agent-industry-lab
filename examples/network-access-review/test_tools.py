import unittest
from agent import assess, REQUESTS, POLICY, execute


class AccessTests(unittest.TestCase):
    def test_out_of_scope(self):
        report = assess(REQUESTS["NET-DEMO-01"], POLICY)
        self.assertEqual(set(report["issues"]), {"destination_outside_demo_scope", "port_not_in_demo_policy"})
        self.assertFalse(report["access_authorized"])

    def test_matching_not_authorized(self):
        report = assess({**REQUESTS["NET-DEMO-01"], "destination": "192.0.2.10", "port": 443}, POLICY)
        self.assertEqual(report["issues"], [])
        self.assertFalse(report["firewall_changed"])

    def test_invalid_port(self):
        with self.assertRaises(ValueError):
            assess({**REQUESTS["NET-DEMO-01"], "port": True}, POLICY)

    def test_scope(self):
        with self.assertRaises(ValueError):
            execute("lookup_request", {"request_id": "other"}, "NET-DEMO-01")


if __name__ == "__main__":
    unittest.main()
