"""Manual acceptance sources; runtime checks are separate from static delivery."""
import copy
import unittest
from agent import PLAN, TASKS, inspect_dependencies, assess, execute


class DependencyTests(unittest.TestCase):
    def entries(self):
        return copy.deepcopy(TASKS["entries"])

    def test_sample(self):
        report = assess(PLAN, TASKS, "2026-11-06T12:00:30Z")
        self.assertEqual(report["ready_pending_tasks"], ["TASK-B"])
        self.assertEqual(report["waiting_tasks"], [{"task_id": "TASK-C", "unfinished_predecessors": ["TASK-B"]}])
        self.assertEqual(report["inconsistent_active_or_done"], [])
        self.assertFalse(report["dispatch_authorized"])

    def test_structural_constraints(self):
        order = inspect_dependencies(self.entries())["structural_order"]
        self.assertLess(order.index("TASK-A"), order.index("TASK-B"))
        self.assertLess(order.index("TASK-B"), order.index("TASK-C"))

    def test_cycle(self):
        entries = self.entries()
        entries[0]["requires"] = ["TASK-C"]
        report = inspect_dependencies(entries)
        self.assertTrue(report["cycle_example"])
        self.assertEqual(report["structural_order"], [])
        self.assertEqual(report["ready_pending_tasks"], [])

    def test_self_cycle(self):
        report = inspect_dependencies([{"task_id": "A", "status": "pending", "requires": ["A"]}])
        self.assertTrue(report["cycle_example"])

    def test_missing_predecessor(self):
        entries = self.entries()
        entries[1]["requires"] = ["OTHER"]
        with self.assertRaises(ValueError):
            inspect_dependencies(entries)

    def test_duplicate_id(self):
        entries = self.entries()
        entries.append(entries[0])
        with self.assertRaises(ValueError):
            inspect_dependencies(entries)

    def test_duplicate_edge(self):
        entries = self.entries()
        entries[1]["requires"] = ["TASK-A", "TASK-A"]
        with self.assertRaises(ValueError):
            inspect_dependencies(entries)

    def test_inconsistent_done(self):
        entries = self.entries()
        entries[2]["status"] = "done"
        self.assertEqual(inspect_dependencies(entries)["inconsistent_active_or_done"][0]["task_id"], "TASK-C")

    def test_running_is_not_ready(self):
        self.assertNotIn("TASK-D", inspect_dependencies(self.entries())["ready_pending_tasks"])

    def test_stale_and_revision(self):
        evidence = {**TASKS, "revision": 1}
        report = assess(PLAN, evidence, "2026-11-06T12:01:01Z")
        self.assertEqual(report["limitations"], ["revision_mismatch", "stale_evidence"])

    def test_future(self):
        with self.assertRaises(ValueError):
            assess(PLAN, TASKS, "2026-11-06T11:59:59Z")

    def test_scope(self):
        with self.assertRaises(ValueError):
            execute("lookup_tasks", {"plan_id": "OTHER"}, PLAN["plan_id"], "2026-11-06T12:00:30Z")
