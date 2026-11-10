import unittest
from agent import PLAN, SCANS, assess, check_digit, execute

AS_OF = "2026-11-10T14:00:30Z"

class LabelTests(unittest.TestCase):
    def test_four_sample_outcomes(self):
        report = assess(PLAN, SCANS, AS_OF)
        self.assertEqual([row["status"] for row in report["boxes"]],
                         ["match", "invalid_check_digit", "wrong_code", "missing_scan"])
        self.assertFalse(report["release_authorized"])

    def test_check_digit_retains_ascii_contract(self):
        self.assertEqual(check_digit("00123"), "6")
        for value in (123, "123", "００１２３"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                check_digit(value)

    def test_empty_and_numeric_are_invalid_format(self):
        for value in ("", 123):
            scans = {**SCANS, "entries": {**SCANS["entries"], "BOX-A": value}}
            with self.subTest(value=value):
                self.assertEqual(assess(PLAN, scans, AS_OF)["boxes"][0]["status"], "invalid_format")

    def test_reject_wrong_scope_and_future(self):
        with self.assertRaises(ValueError):
            execute("lookup_scans", {"job_id": "OTHER"}, PLAN["job_id"], AS_OF)
        with self.assertRaises(ValueError):
            assess(PLAN, SCANS, "2026-11-10T13:59:59Z")
