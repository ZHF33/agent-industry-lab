"""Manual offline checks for bounded search, length conservation and objective ties."""
import unittest
from agent import POLICY, assess, execute, load_snapshot

AS_OF = "2026-11-26T12:30:30Z"

class ToolTests(unittest.TestCase):
    def test_reference_beats_longest_first(self):
        result=assess(load_snapshot(),POLICY,AS_OF)
        self.assertEqual([r["piece_id"] for r in result["selected"]],["P-02","P-03"])
        self.assertEqual((result["delivered_mm"],result["kerf_loss_mm"],result["remainder_mm"]),(900,10,90))
        self.assertEqual((result["candidates_checked"],result["feasible_candidates"]),(8,5))
        self.assertEqual(result["delivered_mm"]+result["kerf_loss_mm"]+result["remainder_mm"],1000)
        self.assertFalse(result["saw_actions_executed"])

    def test_input_order_invariance(self):
        snapshot=load_snapshot()
        expected=assess(snapshot,POLICY,AS_OF)
        snapshot["requests"].reverse()
        self.assertEqual(assess(snapshot,POLICY,AS_OF),expected)

    def test_fewer_cuts_then_ids(self):
        snapshot=load_snapshot()
        snapshot["requests"].append({"piece_id":"P-04","length_mm":900})
        self.assertEqual([r["piece_id"] for r in assess(snapshot,POLICY,AS_OF)["selected"]],["P-04"])
        snapshot["length_mm"]=500
        snapshot["requests"]=[{"piece_id":"Z","length_mm":300},{"piece_id":"A","length_mm":300}]
        self.assertEqual([r["piece_id"] for r in assess(snapshot,POLICY,AS_OF)["selected"]],["A"])

    def test_exact_capacity_and_no_piece_fits(self):
        snapshot=load_snapshot()
        snapshot["length_mm"]=910
        self.assertEqual(assess(snapshot,POLICY,AS_OF)["remainder_mm"],0)
        snapshot["length_mm"]=909
        self.assertEqual(assess(snapshot,POLICY,AS_OF)["delivered_mm"],600)
        snapshot["length_mm"]=400
        self.assertEqual(assess(snapshot,POLICY,AS_OF)["status"],"no_piece_fits")

    def test_budget_and_invalid_data(self):
        for kind in ("budget","duplicate","boolean","unit","incomplete"):
            snapshot=load_snapshot()
            if kind=="budget":
                snapshot["requests"]=[{"piece_id":str(i),"length_mm":10} for i in range(11)]
            elif kind=="duplicate":
                snapshot["requests"].append(dict(snapshot["requests"][0]))
            elif kind=="boolean":
                snapshot["requests"][0]["length_mm"]=True
            elif kind=="unit":
                snapshot["unit"]="cm"
            else:
                snapshot["declared_complete"]=False
            with self.assertRaises(ValueError):
                assess(snapshot,POLICY,AS_OF)

    def test_scope_material_and_age(self):
        with self.assertRaises(ValueError):
            execute("plan_cut",{"stock_id":"OTHER"},"BAR-DEMO-A",AS_OF,load_snapshot())
        snapshot=load_snapshot()
        snapshot["material_id"]="OTHER"
        with self.assertRaises(ValueError):
            assess(snapshot,POLICY,AS_OF)
        self.assertEqual(assess(load_snapshot(),POLICY,"2026-11-26T12:31:00Z")["delivered_mm"],900)
        for time in ("2026-11-26T12:31:01Z","2026-11-26T12:29:59Z"):
            with self.assertRaises(ValueError):
                assess(load_snapshot(),POLICY,time)

if __name__ == "__main__":
    unittest.main()
