"""Offline unit-contract lesson reuses the Agent conversion; no model or network."""
from pathlib import Path
from fractions import Fraction
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "examples" / "cold-chain-excursion-review"))
from agent import celsius

if __name__ == "__main__":
    print("50F in C:", celsius("50", "F"))
    print("8C in band:", Fraction(2) <= celsius("8", "C") <= Fraction(8))
    print("18F difference in C:", Fraction(18) * Fraction(5, 9))
    print("18F absolute in C:", celsius("18", "F"))
    try:
        celsius("4", "unknown")
    except ValueError as error:
        print("invalid:", error)
