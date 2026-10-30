"""Approval boundary cases; no model, identity provider or business operations."""
from copy import deepcopy
import unittest
from agent import REQUESTS, assess, execute
AT="2026-10-30T12:00:30+00:00"
class ToolTests(unittest.TestCase):
    def evidence(self): return deepcopy(REQUESTS["REQUEST-DEMO-01"])
    def test_exact_expiry(self): self.assertIn("approval_expired", assess(self.evidence(),AT)["blocking_reasons"])
    def test_before_expiry_not_authorization(self):
        result=assess(self.evidence(),"2026-10-30T12:00:29+00:00")
        self.assertEqual(result["blocking_reasons"],[])
        self.assertFalse(result["execution_authorized"])
    def test_scope_changed(self):
        e=self.evidence(); e["request"]["scope"]="OTHER"
        self.assertIn("scope_or_action_mismatch",assess(e,AT)["blocking_reasons"])
    def test_revision_changed(self):
        e=self.evidence(); e["request"]["revision"]=3
        self.assertIn("revision_mismatch",assess(e,AT)["blocking_reasons"])
    def test_revoked(self):
        e=self.evidence(); e["approval"]["revoked"]=True
        self.assertIn("approval_revoked",assess(e,AT)["blocking_reasons"])
    def test_consumed(self):
        e=self.evidence(); e["approval"]["consumed"]=True
        self.assertIn("approval_already_consumed",assess(e,AT)["blocking_reasons"])
    def test_unknown_reviewer(self):
        e=self.evidence(); e["approval"]["reviewer"]="unknown"
        self.assertIn("reviewer_not_allowed",assess(e,AT)["blocking_reasons"])
    def test_stale(self): self.assertIn("stale_evidence",assess(self.evidence(),"2026-10-30T12:02:00+00:00")["blocking_reasons"])
    def test_future(self):
        with self.assertRaises(ValueError): assess(self.evidence(),"2026-10-30T11:59:00+00:00")
    def test_invalid_interval(self):
        e=self.evidence(); e["approval"]["expires_at"]=e["approval"]["approved_at"]
        with self.assertRaises(ValueError): assess(e,AT)
    def test_not_approved(self):
        e=self.evidence(); e["approval"]["decision"]="reject"
        self.assertIn("not_approved",assess(e,AT)["blocking_reasons"])
    def test_request_mismatch(self):
        e=self.evidence(); e["approval"]["request_id"]="OTHER"
        self.assertIn("request_mismatch",assess(e,AT)["blocking_reasons"])
    def test_tool_scope(self):
        with self.assertRaises(ValueError): execute("lookup_approval",{"request_id":"OTHER"},"REQUEST-DEMO-01",AT)
    def test_flag_not_boolean(self):
        e=self.evidence(); e["approval"]["consumed"]="false"
        with self.assertRaises(ValueError): assess(e,AT)
if __name__=="__main__": unittest.main()
