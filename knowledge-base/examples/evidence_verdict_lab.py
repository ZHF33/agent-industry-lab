"""Preserve known failures alongside missing required observations."""


def verdict(required, observed):
    if not required:
        raise ValueError("required checklist is empty")
    failed = [key for key in required if observed.get(key) is False]
    missing = [key for key in required if key not in observed]
    state = "blocked" if failed else "needs_evidence" if missing else "ready_for_review"
    return state, failed, missing


if __name__ == "__main__":
    required = ["repair", "trial", "return"]
    for observed in (
        {"repair": True, "trial": False},
        {"repair": True, "trial": True},
        {"repair": True, "trial": True, "return": True},
    ):
        state, failed, missing = verdict(required, observed)
        print(f"{state} failed={failed} missing={missing}")
    print("all_empty", all([]))
