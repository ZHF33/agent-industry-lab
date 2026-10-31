"""Synthetic decision-routing illustration, no actual automatic action."""

def route(evidence_complete, authorized, reversible, review_required):
    flags=(evidence_complete,authorized,reversible,review_required)
    if any(type(value) is not bool for value in flags):
        raise ValueError("Boolean flags required")
    if not evidence_complete: return "request_evidence"
    if not authorized: return "deny_execution"
    if review_required or not reversible: return "human_review"
    return "candidate_for_bounded_automation_not_execution"

if __name__=="__main__":
    cases=[("missing",False,True,True,False),
           ("unauthorized",True,False,True,False),
           ("irreversible",True,True,False,False),
           ("review_policy",True,True,True,True),
           ("bounded_candidate",True,True,True,False)]
    for name,*flags in cases: print(name+":",route(*flags))
    try: route(True,"yes",True,False)
    except ValueError as error: print("invalid:",error)
