"""Synthetic revision boundaries; no live records or models."""
from copy import deepcopy
import unittest
from agent import CHANGES, assess, execute
AT="2026-10-28T12:00:30+00:00"
class ToolTests(unittest.TestCase):
    def evidence(self): return deepcopy(CHANGES["CHANGE-DEMO-01"])
    def test_conflict(self): self.assertEqual(assess(self.evidence(),AT)["status"],"revision_conflict")
    def test_match_not_write(self):
        e=self.evidence(); e["proposal"]["base_revision"]=5
        result=assess(e,AT)
        self.assertEqual(result["status"],"matching_snapshot_requires_review")
        self.assertFalse(result["write_authorized"])
    def test_missing_base(self):
        e=self.evidence(); e["proposal"]["base_revision"]=None
        self.assertEqual(assess(e,AT)["status"],"missing_base_revision")
    def test_closed(self):
        e=self.evidence(); e["proposal"]["base_revision"]=5; e["record"]["status"]="closed"
        self.assertEqual(assess(e,AT)["status"],"closed_record_requires_review")
    def test_identity(self):
        e=self.evidence(); e["record"]["record_id"]="OTHER"
        self.assertEqual(assess(e,AT)["status"],"insufficient_evidence")
    def test_stale(self): self.assertEqual(assess(self.evidence(),"2026-10-28T12:02:00+00:00")["status"],"insufficient_evidence")
    def test_future(self):
        with self.assertRaises(ValueError): assess(self.evidence(),"2026-10-28T11:59:00+00:00")
    def test_bool_revision(self):
        e=self.evidence(); e["proposal"]["base_revision"]=True
        with self.assertRaises(ValueError): assess(e,AT)
    def test_invalid_patch(self):
        e=self.evidence(); e["proposal"]["patch"]["status"]="open"
        with self.assertRaises(ValueError): assess(e,AT)
    def test_scope(self):
        with self.assertRaises(ValueError): execute("lookup_record",{"change_id":"OTHER"},"CHANGE-DEMO-01",AT)
    def test_no_timezone(self):
        with self.assertRaises(ValueError): assess(self.evidence(),"2026-10-28T12:00:30")
    def test_future_base_revision(self):
        e=self.evidence(); e["proposal"]["base_revision"]=6
        self.assertEqual(assess(e,AT)["status"],"revision_conflict")
if __name__=="__main__": unittest.main()
