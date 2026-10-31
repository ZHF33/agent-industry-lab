"""Pure approval-window check; no identity system, secrets, state mutation or network."""
from datetime import datetime

def check(approval, as_of, revision):
    now, end = datetime.fromisoformat(as_of), datetime.fromisoformat(approval["expires_at"])
    if any(t.tzinfo is None or t.utcoffset() is None for t in (now,end)):
        raise ValueError("Timezone required")
    reasons=[]
    if revision != approval["revision"]: reasons.append("revision_changed")
    if now >= end: reasons.append("expired")
    if approval["revoked"]: reasons.append("revoked")
    if approval["consumed"]: reasons.append("consumed")
    return reasons or ["snapshot_eligible_not_execution_authority"]

if __name__ == "__main__":
    approval={"revision":2,"expires_at":"2026-10-30T12:00:30+00:00","revoked":False,"consumed":False}
    print("before:",check(approval,"2026-10-30T12:00:29+00:00",2))
    print("boundary:",check(approval,"2026-10-30T12:00:30+00:00",2))
    print("changed:",check(approval,"2026-10-30T12:00:29+00:00",3))
    print("replay:",check({**approval,"consumed":True},"2026-10-30T12:00:29+00:00",2))
