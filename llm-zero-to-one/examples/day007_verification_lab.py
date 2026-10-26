"""Artificial next-choice weights versus exact arithmetic; no model inference."""
from decimal import Decimal, InvalidOperation

# These labels stand for complete answer choices in a toy, not real model tokens.
WEIGHTS = {"8.00": 0.8, "7.50": 0.2}

def verify_total(prices, claimed):
    try:
        values = [Decimal(x) for x in prices]
        claim = Decimal(claimed)
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ValueError("Decimal price text required") from error
    if not values or not all(v.is_finite() and v >= 0 for v in values) or not claim.is_finite():
        raise ValueError("Finite non-negative prices and finite claim required")
    expected = sum(values, Decimal("0"))
    return format(expected, ".2f"), claim == expected

if __name__ == "__main__":
    selected = max(WEIGHTS, key=WEIGHTS.get)
    exact, passed = verify_total(["3.20", "4.30"], selected)
    print("toy_choice:", selected)
    print("exact_total:", exact)
    print("claim_matches:", passed)
    exact, passed = verify_total(["3.20", "4.30"], "7.50")
    print("corrected_matches:", passed)
    try:
        verify_total(["NaN"], "0.00")
    except ValueError as error:
        print("invalid:", error)
