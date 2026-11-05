"""Manual acceptance cases for synthetic evidence."""
import copy
import unittest
from agent import EXPORT, PAGES, assess, inspect_pages, execute


class ExportTests(unittest.TestCase):
    def pages(self):
        return copy.deepcopy(PAGES["entries"])

    def test_sample(self):
        report = assess(EXPORT, PAGES, "2026-11-05T12:00:30Z")
        self.assertEqual(report["unique_count"], 3)
        self.assertEqual(report["row_count"], 4)
        self.assertEqual(report["duplicate_ids"], ["ROW-2"])
        self.assertEqual(report["blocked_cursor"], "P2")
        self.assertFalse(report["terminal_seen"])

    def test_complete(self):
        pages = self.pages()
        pages[1].update(ids=["ROW-3", "ROW-4"], next_cursor=None)
        report = inspect_pages(EXPORT, pages)
        self.assertTrue(report["terminal_seen"])
        self.assertEqual(report["reasons"], [])

    def test_cycle(self):
        pages = self.pages()
        pages[1]["next_cursor"] = "P0"
        self.assertIn("cursor_cycle", inspect_pages(EXPORT, pages)["reasons"])

    def test_budget(self):
        self.assertIn("page_budget_exhausted", inspect_pages(EXPORT, self.pages(), 1)["reasons"])

    def test_snapshot(self):
        pages = self.pages()
        pages[1]["snapshot"] = "OTHER"
        self.assertIn("snapshot_mismatch", inspect_pages(EXPORT, pages)["reasons"])

    def test_unused(self):
        pages = self.pages()
        pages[0]["next_cursor"] = None
        self.assertEqual(inspect_pages(EXPORT, pages)["unused_cursors"], ["P1"])

    def test_duplicate_page(self):
        pages = self.pages()
        pages.append(pages[0])
        with self.assertRaises(ValueError):
            inspect_pages(EXPORT, pages)

    def test_empty_terminal(self):
        page = {"source": "empty", "cursor": "P0", "next_cursor": None, "snapshot": "SNAP-A", "ids": []}
        self.assertEqual(inspect_pages({**EXPORT, "expected_unique": 0}, [page])["reasons"], [])

    def test_count_type(self):
        with self.assertRaises(ValueError):
            inspect_pages({**EXPORT, "expected_unique": True}, self.pages())

    def test_stale_and_future(self):
        self.assertIn("stale_evidence", assess(EXPORT, PAGES, "2026-11-05T12:01:01Z")["reasons"])
        with self.assertRaises(ValueError):
            assess(EXPORT, PAGES, "2026-11-05T11:59:59Z")

    def test_scope(self):
        with self.assertRaises(ValueError):
            execute("lookup_pages", {"export_id": "OTHER"}, EXPORT["export_id"], "2026-11-05T12:00:30Z")
