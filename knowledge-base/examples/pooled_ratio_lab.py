"""Synthetic example of pooled inspection counts."""
from fractions import Fraction


def report(rows):
    if any(row is None for row in rows):
        return "missing_line", None
    passed = sum(row[0] for row in rows)
    inspected = sum(row[1] for row in rows)
    if not inspected:
        return "no_inspections", None
    return "ready", Fraction(passed, inspected)


def main():
    for label, rows in (
        ("closed", [(90, 90), (5, 10), (0, 0)]),
        ("missing", [(90, 90), (5, 10), None]),
        ("empty", [(0, 0), (0, 0), (0, 0)]),
    ):
        status, ratio = report(rows)
        print(f"{label}: {status} {ratio}")


if __name__ == "__main__":
    main()
