"""Teaching arithmetic only, not the full quotation validator."""
from decimal import Decimal, ROUND_HALF_UP


def calculate(unit_price, quantity, freight):
    if freight is None:
        return "unknown freight"
    return str((Decimal(unit_price) * quantity + Decimal(freight)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


if __name__ == "__main__":
    print("A", calculate("10.20", 100, "20.00"))
    print("B", calculate("9.90", 100, "80.00"))
    print("C", calculate("9.00", 100, None))
    print(Decimal("0.1") + Decimal("0.2"))
