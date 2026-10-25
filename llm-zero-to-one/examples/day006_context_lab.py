"""Manual budget units, NOT tokenizer counts; no model or network."""
MANDATORY = [("rules", 12), ("question", 8)]
OPTIONAL = [("receipt_evidence", 14), ("recent_history", 10), ("old_smalltalk", 16)]


def choose_context(window, reserved_output, overhead):
    if any(type(x) is not int or x < 0 for x in (window, reserved_output, overhead)):
        raise ValueError("Non-negative integer budgets required")
    capacity = window - reserved_output - overhead
    used = sum(cost for _, cost in MANDATORY)
    if used > capacity:
        raise ValueError("Mandatory content does not fit; do not silently drop it")
    selected = [name for name, _ in MANDATORY]
    skipped = []
    for name, cost in OPTIONAL:
        if used + cost <= capacity:
            selected.append(name)
            used += cost
        else:
            skipped.append(name)
    return selected, skipped, used, capacity


if __name__ == "__main__":
    for window in (64, 80):
        selected, skipped, used, capacity = choose_context(window, 16, 4)
        print(f"window={window} input={used}/{capacity}")
        print("selected:", ", ".join(selected))
        print("skipped:", ", ".join(skipped) or "none")
    try:
        choose_context(32, 16, 4)
    except ValueError as error:
        print("overflow:", error)
