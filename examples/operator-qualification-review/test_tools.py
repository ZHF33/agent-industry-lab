"""Manual offline contracts and an independent exhaustive small-graph oracle."""
import copy
import itertools
import unittest
from agent import POLICY, assess, execute, load_snapshot, maximum_matching

AS_OF = "2026-11-25T12:30:30Z"

class ToolTests(unittest.TestCase):
    def test_reference_assignment_rearranges_first_choice(self):
        result=assess(load_snapshot(),POLICY,AS_OF)
        self.assertEqual(result["pairs"],[{"job_id":"J-01","operator_id":"OP-B"},
                                          {"job_id":"J-02","operator_id":"OP-A"}])
        self.assertEqual(result["unmatched_jobs"],["J-03"])
        self.assertEqual(result["attempts"][0]["after"],[{"job_id":"J-01","operator_id":"OP-A"}])
        self.assertEqual(result["matched_count"],2)
        self.assertFalse(result["roster_actions_executed"])

    def test_available_scan_operator_fills_remaining_job(self):
        snapshot=load_snapshot()
        snapshot["operators"][2]["available"]=True
        self.assertEqual(assess(snapshot,POLICY,AS_OF)["status"],"full_proposal")

    def test_empty_and_multiple_required_skills(self):
        snapshot=load_snapshot()
        snapshot["operators"]=[]
        self.assertEqual(assess(snapshot,POLICY,AS_OF)["matched_count"],0)
        policy=copy.deepcopy(POLICY)
        policy["jobs"]=[{"job_id":"COMBINED","required_skills":["PACK","LABEL"]}]
        self.assertEqual(assess(load_snapshot(),policy,AS_OF)["pairs"],
                         [{"job_id":"COMBINED","operator_id":"OP-A"}])

    def test_bad_evidence_rejected(self):
        for kind in ("duplicate","flag","incomplete","skill"):
            snapshot=load_snapshot()
            if kind=="duplicate":
                snapshot["operators"].append(dict(snapshot["operators"][0]))
            elif kind=="flag":
                snapshot["operators"][0]["available"]=1
            elif kind=="incomplete":
                snapshot["declared_complete"]=False
            else:
                snapshot["operators"][0]["approved_skills"]=["PACK","PACK"]
            with self.assertRaises(ValueError):
                assess(snapshot,POLICY,AS_OF)

    def test_scope_and_age(self):
        with self.assertRaises(ValueError):
            execute("match_operators",{"plan_id":"OTHER"},"PLAN-DEMO-A",AS_OF,load_snapshot())
        self.assertEqual(assess(load_snapshot(),POLICY,"2026-11-25T12:31:00Z")["matched_count"],2)
        for time in ("2026-11-25T12:31:01Z","2026-11-25T12:29:59Z"):
            with self.assertRaises(ValueError):
                assess(load_snapshot(),POLICY,time)

    def test_all_three_by_three_graphs_against_enumeration(self):
        jobs=["A","B","C"]
        operators=["1","2","3"]
        for bits in range(1<<9):
            eligible={job:[operator for j,operator in enumerate(operators) if bits & (1<<(i*3+j))]
                      for i,job in enumerate(jobs)}
            optimum=0
            for proposed in itertools.product([None]+operators,repeat=3):
                chosen=[operator for operator in proposed if operator is not None]
                if len(chosen)!=len(set(chosen)):
                    continue
                if all(operator is None or operator in eligible[job] for job,operator in zip(jobs,proposed)):
                    optimum=max(optimum,len(chosen))
            pairs,_=maximum_matching(eligible)
            self.assertEqual(len(pairs),optimum)
            self.assertEqual(len({r["operator_id"] for r in pairs}),len(pairs))
            self.assertEqual(len({r["job_id"] for r in pairs}),len(pairs))
            self.assertTrue(all(r["operator_id"] in eligible[r["job_id"]] for r in pairs))

if __name__ == "__main__":
    unittest.main()
