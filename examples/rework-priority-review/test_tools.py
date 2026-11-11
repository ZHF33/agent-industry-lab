import unittest
from agent import BACKLOG, execute, rank

AS_OF = "2026-11-11T15:30:00Z"

class RankingTests(unittest.TestCase):
    def test_order_missing_and_overdue(self):
        report = rank(BACKLOG, AS_OF)
        self.assertEqual([row["job_id"] for row in report["ordered"]],
                         ["RW-002", "RW-003", "RW-001"])
        self.assertEqual([row["overdue"] for row in report["ordered"]], [False, False, True])
        self.assertEqual(report["needs_evidence"][0]["missing"], ["severity", "due_at"])
        self.assertFalse(report["dispatch_authorized"])

    def test_tie_break_is_independent_of_input_order(self):
        jobs = list(reversed(BACKLOG["jobs"]))
        result = rank({**BACKLOG, "jobs": jobs}, AS_OF)
        self.assertEqual(result["ordered"], rank(BACKLOG, AS_OF)["ordered"])

    def test_reject_bool_and_duplicates(self):
        job = BACKLOG["jobs"][0]
        for rows in ([{**job, "severity": True}], [job, job]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                rank({**BACKLOG, "jobs": rows}, AS_OF)

    def test_reject_wrong_scope_and_future(self):
        with self.assertRaises(ValueError):
            execute("lookup_jobs", {"line_id": "OTHER"}, BACKLOG["line_id"], AS_OF)
        with self.assertRaises(ValueError):
            rank(BACKLOG, "2026-11-11T14:59:59Z")
