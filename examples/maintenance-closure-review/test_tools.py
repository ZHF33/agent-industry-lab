import unittest

from agent import PLAN, POLICY, assess, execute


AS_OF = "2026-11-20T13:15:00Z"


class ClosureTests(unittest.TestCase):
    def test_known_failure_keeps_missing_visible(self):
        report = assess(PLAN, POLICY, AS_OF)
        self.assertEqual(report["verdict"], "blocked")
        self.assertEqual(report["failed_checks"], ["trial_record"])
        self.assertEqual(report["missing_checks"], ["parts_return"])

    def test_repairing_failure_leaves_unknown(self):
        evidence = {**PLAN, "checks": {**PLAN["checks"], "trial_record": {"source": "trial-revised", "passed": True}}}
        report = assess(evidence, POLICY, AS_OF)
        self.assertEqual(report["verdict"], "needs_evidence")
        evidence["checks"]["parts_return"] = {"source": "return-demo-01", "passed": True}
        self.assertEqual(assess(evidence, POLICY, AS_OF)["verdict"], "ready_for_review")

    def test_empty_policy_and_coerced_booleans_rejected(self):
        with self.assertRaises(ValueError):
            assess(PLAN, {**POLICY, "required": []}, AS_OF)
        for value in ("false", 0, None):
            evidence = {**PLAN, "checks": {"repair_record": {"source": "bad", "passed": value}}}
            with self.subTest(value=value), self.assertRaises(ValueError):
                assess(evidence, POLICY, AS_OF)

    def test_no_observations_needs_evidence(self):
        report = assess({**PLAN, "checks": {}}, POLICY, AS_OF)
        self.assertEqual(report["verdict"], "needs_evidence")
        self.assertEqual(len(report["missing_checks"]), 3)

    def test_scope_and_future_snapshot(self):
        order = POLICY["order_id"]
        with self.assertRaises(ValueError):
            execute("lookup_evidence", {"order_id": "OTHER"}, order, AS_OF)
        with self.assertRaises(ValueError):
            execute("lookup_evidence", {"order_id": order}, order, "2026-11-20T12:59:59Z")
