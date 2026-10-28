"""Sequential in-memory CAS illustration, not concurrent storage or a business write."""
from copy import deepcopy

START = {"revision": 4, "priority": "normal"}

def compare_and_swap(record, expected, priority):
    if type(expected) is not int or expected < 1 or priority not in {"low", "normal", "high"}:
        raise ValueError("Invalid expected revision or priority")
    if record["revision"] != expected:
        return False, dict(record)
    return True, {"revision": expected+1, "priority": priority}

if __name__ == "__main__":
    record = deepcopy(START)
    ok, record = compare_and_swap(record, 4, "low")
    print("A:", ok, record["revision"], record["priority"])
    ok, unchanged = compare_and_swap(record, 4, "high")
    print("B stale:", ok, unchanged["revision"], unchanged["priority"])
    ok, record = compare_and_swap(record, 5, "high")
    print("B re-reviewed:", ok, record["revision"], record["priority"])
