"""Manual acceptance sources; no model, filesystem attachment access or test execution on delivery."""
import copy
import unittest
from agent import BATCHES, assess, path_issues, execute

AS_OF = "2026-11-02T12:00:30+00:00"


class ToolTests(unittest.TestCase):
    def fixture(self): return copy.deepcopy(BATCHES["BATCH-DEMO-01"])

    def test_normal_relative_path(self): self.assertEqual(path_issues("docs/spec.pdf"), [])

    def test_dot_segments(self):
        for p in ["../x.csv", "a/../x.pdf", "a/./x.pdf", "a//x.pdf"]:
            with self.subTest(path=p): self.assertTrue(path_issues(p))

    def test_platform_paths(self):
        for p in ["/x.pdf", "C:/x.pdf", "C:x.pdf", "\\\\server\\x.pdf", "a\\x.pdf"]:
            with self.subTest(path=p): self.assertTrue(path_issues(p))

    def test_ambiguous_and_reserved(self):
        for p in ["%2e%2e/x.pdf", "a:b.pdf", "CON.pdf", "a/NUL.csv", "a/ending.", "a/中文.pdf"]:
            with self.subTest(path=p): self.assertTrue(path_issues(p))

    def test_sample_report(self):
        r = assess(self.fixture(), AS_OF)
        self.assertEqual(r["exception_entry_count"], 2)
        self.assertEqual(r["declared_total_bytes"], 6002148)
        self.assertEqual(r["entries"][0]["malware_status"], "unknown")
        self.assertFalse(r["import_authorized"])
        self.assertFalse(r["files_opened"])

    def test_declared_type_mismatch(self):
        r = assess(self.fixture(), AS_OF)
        self.assertIn("declared_type_mismatch", r["entries"][2]["reasons"])

    def test_size_equality_allowed(self):
        d=self.fixture(); d["manifest"]["entries"] = [d["manifest"]["entries"][0]]
        d["manifest"]["entries"][0]["declared_bytes"] = 5000000
        r=assess(d, AS_OF); self.assertEqual(r["exception_entry_count"], 0)
        self.assertFalse(r["import_authorized"])

    def test_boolean_size_rejected(self):
        d=self.fixture(); d["manifest"]["entries"][0]["declared_bytes"]=True
        with self.assertRaises(ValueError): assess(d, AS_OF)

    def test_duplicate_identity(self):
        d=self.fixture(); d["manifest"]["entries"][1]["entry_id"]="ATT-1"
        with self.assertRaises(ValueError): assess(d, AS_OF)

    def test_duplicate_path_casefold(self):
        d=self.fixture(); d["manifest"]["entries"][1]["path"]="DOCS/SPEC.PDF"
        self.assertIn("duplicate_path", assess(d, AS_OF)["entries"][1]["reasons"])

    def test_stale_and_future(self):
        self.assertIn("stale_snapshot", assess(self.fixture(), "2026-11-02T12:01:01+00:00")["reasons"])
        with self.assertRaises(ValueError): assess(self.fixture(), "2026-11-02T11:59:59+00:00")

    def test_scope_and_unknown_tools(self):
        for name,args in [("open_file",{"batch_id":"BATCH-DEMO-01"}), ("lookup_manifest",{"batch_id":"OTHER"}),
                          ("lookup_manifest",{"batch_id":"BATCH-DEMO-01","path":"x.pdf"})]:
            with self.assertRaises(ValueError): execute(name,args,"BATCH-DEMO-01",AS_OF)

    def test_wrong_batch(self):
        d=self.fixture(); d["manifest"]["batch_id"]="OTHER"
        with self.assertRaises(ValueError): assess(d, AS_OF)


if __name__ == "__main__": unittest.main()
