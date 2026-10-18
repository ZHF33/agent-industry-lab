import unittest
from agent import classify, INCIDENTS, OBSERVATIONS, execute


class FailureTests(unittest.TestCase):
    def test_unknown_write(self):
        result = classify(INCIDENTS["API-DEMO-01"], OBSERVATIONS["API-DEMO-01"])
        self.assertEqual(result["rows"][1]["category"], "outcome_unknown")
        self.assertTrue(all(r["reconcile_before_resubmitting"] for r in result["rows"]))
        self.assertFalse(any(r["automatic_retry"] for r in result["rows"]))

    def test_read_candidate(self):
        result = classify({**INCIDENTS["API-DEMO-01"], "method": "GET"}, OBSERVATIONS["API-DEMO-01"])
        self.assertTrue(result["rows"][0]["retry_candidate_for_human_review"])

    def test_authorization(self):
        result = classify(INCIDENTS["API-DEMO-01"], [{"source": "demo", "kind": "http", "status": 403}])
        self.assertEqual(result["rows"][0]["category"], "authorization_or_policy")

    def test_scope(self):
        with self.assertRaises(ValueError):
            execute("lookup_incident", {"incident_id": "other"}, "API-DEMO-01")


if __name__ == "__main__":
    unittest.main()
