"""Boundary tests for synthetic projections; no inference/network calls."""
from copy import deepcopy
from fractions import Fraction
import unittest
from agent import SERVICES, assess, project, execute
AT="2026-10-27T12:00:02.500000+00:00"
class ToolTests(unittest.TestCase):
    def record(self): return deepcopy(SERVICES["SERVICE-DEMO-01"])
    def test_sample(self):
        result=assess(self.record(),AT)
        self.assertEqual(result["projected_tokens"],"8")
        self.assertEqual(result["projection_outcome"],"batch_exceeds_capacity")
        self.assertIsNone(result["ideal_wait_seconds"])
    def test_exact_wait(self):
        self.assertEqual(project(10,3,"2",Fraction(5,2),9)["ideal_wait_seconds"],"1/2")
    def test_cap(self): self.assertEqual(project(10,3,"2",Fraction(100),10)["projected_tokens"],"10")
    def test_zero_refill(self): self.assertIsNone(project(10,3,"0",Fraction(5),4)["ideal_wait_seconds"])
    def test_at_boundary(self): self.assertEqual(project(10,3,"2",Fraction(5,2),8)["ideal_wait_seconds"],"0")
    def test_stale(self): self.assertEqual(assess(self.record(),"2026-10-27T12:02:00+00:00")["projection_outcome"],"insufficient_evidence")
    def test_version_mismatch(self):
        r=self.record(); r["traffic"]["limit_version"]="old"
        self.assertIsNone(assess(r,AT)["projected_tokens"])
    def test_scope_mismatch(self):
        r=self.record(); r["limit"]["service_id"]="OTHER"
        self.assertIsNone(assess(r,AT)["projected_tokens"])
    def test_future(self):
        with self.assertRaises(ValueError): assess(self.record(),"2026-10-27T11:59:00+00:00")
    def test_invalid_tokens(self):
        with self.assertRaises(ValueError): project(10,11,"2",Fraction(0),1)
    def test_negative_refill(self):
        with self.assertRaises(ValueError): project(10,3,"-1",Fraction(0),1)
    def test_bool_not_integer(self):
        with self.assertRaises(ValueError): project(10,True,"2",Fraction(0),1)
    def test_tool_scope(self):
        with self.assertRaises(ValueError): execute("lookup_limit",{"service_id":"OTHER"},"SERVICE-DEMO-01",AT)
    def test_naive_time(self):
        with self.assertRaises(ValueError): assess(self.record(),"2026-10-27T12:00:02")
if __name__=="__main__": unittest.main()
