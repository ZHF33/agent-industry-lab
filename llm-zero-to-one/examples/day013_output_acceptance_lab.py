"""Offline layered validation against one synthetic evidence set, not an executor."""
import json

EXPECTED = {"LOT-MIX-B", "LOT-PACK-C", "LOT-SHIP-D"}


def validate(raw):
    try: value=json.loads(raw)
    except (ValueError, TypeError): return "parse_error"
    if (not isinstance(value, dict) or set(value) != {"candidate_count", "candidate_lots", "actions_executed"}
            or type(value["candidate_count"]) is not int or value["candidate_count"] < 0
            or not isinstance(value["candidate_lots"], list)
            or not all(isinstance(x,str) for x in value["candidate_lots"])
            or type(value["actions_executed"]) is not bool): return "contract_error"
    rows=value["candidate_lots"]
    if value["candidate_count"] != len(rows) or len(set(rows)) != len(rows): return "consistency_error"
    if set(rows) != EXPECTED: return "evidence_mismatch"
    if value["actions_executed"]: return "action_claim_rejected"
    return "accepted_for_human_review_not_execution"


if __name__ == "__main__":
    good={"candidate_count":3,"candidate_lots":sorted(EXPECTED),"actions_executed":False}
    cases={"bad_json":"{", "wrong_type":json.dumps({**good,"candidate_count":"3"}),
           "wrong_count":json.dumps({**good,"candidate_count":2}),
           "wrong_evidence":json.dumps({**good,"candidate_lots":["OTHER","LOT-PACK-C","LOT-SHIP-D"]}),
           "false_action":json.dumps({**good,"actions_executed":True}), "good":json.dumps(good)}
    for name, raw in cases.items(): print(name+":",validate(raw))
