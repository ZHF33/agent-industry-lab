"""Synthetic retrieval boundaries, no live model or business API."""
from copy import deepcopy
import unittest
from agent import REQUESTS, DOCUMENTS, retrieve, assess, execute
AT = "2026-10-26T12:00:30+00:00"

class ToolTests(unittest.TestCase):
    def request(self): return deepcopy(REQUESTS["REQUEST-DEMO-01"])
    def test_scope_and_effective_filters(self):
        result = retrieve(self.request(), DOCUMENTS, AT)
        self.assertEqual([x["source"] for x in result["hits"]], ["KB-DEMO-RETURN-v2"])
        self.assertEqual(result["hits"][0]["overlap_score"], 3)
    def test_no_hits(self):
        request = self.request(); request["query"] = "warranty kettle"
        self.assertEqual(assess(request, DOCUMENTS, AT)["status"], "insufficient_evidence")
    def test_region(self):
        request = self.request(); request["region"] = "OTHER"
        self.assertEqual(retrieve(request, DOCUMENTS, AT)["hits"], [])
    def test_stale(self):
        self.assertEqual(retrieve(self.request(), DOCUMENTS, "2026-10-26T12:02:00+00:00")["hits"], [])
    def test_future(self):
        with self.assertRaises(ValueError): retrieve(self.request(), DOCUMENTS, "2026-10-26T11:59:00+00:00")
    def test_duplicate_sources(self):
        with self.assertRaises(ValueError): retrieve(self.request(), DOCUMENTS+[DOCUMENTS[0]], AT)
    def test_expiry_boundary(self):
        docs=deepcopy(DOCUMENTS); docs[0]["effective_until"]=AT
        self.assertEqual(retrieve(self.request(), docs, AT)["hits"], [])
    def test_no_eligibility_claim(self):
        report=assess(self.request(), DOCUMENTS, AT)
        self.assertFalse(report["eligibility_verified"])
        self.assertFalse(report["answer_entailment_verified"])
    def test_tool_scope(self):
        with self.assertRaises(ValueError): execute("search_knowledge", {"request_id":"OTHER"}, "REQUEST-DEMO-01", AT)
    def test_no_searchable_terms(self):
        request=self.request(); request["query"]="?!"
        with self.assertRaises(ValueError): retrieve(request, DOCUMENTS, AT)
    def test_bad_interval(self):
        docs=deepcopy(DOCUMENTS); docs[0]["effective_until"]=docs[0]["effective_from"]
        with self.assertRaises(ValueError): retrieve(self.request(), docs, AT)
    def test_no_timezone(self):
        with self.assertRaises(ValueError): retrieve(self.request(), DOCUMENTS, "2026-10-26T12:00:30")

if __name__ == "__main__": unittest.main()
