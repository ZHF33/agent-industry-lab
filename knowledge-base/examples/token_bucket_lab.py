"""Offline token-bucket budget projection; no sleeping, networking or shared state."""
from fractions import Fraction

def budget(capacity, tokens, rate, elapsed, demand):
    if any(type(v) is not int for v in (capacity, tokens, demand)) or capacity <= 0 or not 0 <= tokens <= capacity or demand <= 0:
        raise ValueError("Invalid integer capacity/tokens/demand")
    rate, elapsed = Fraction(rate), Fraction(elapsed)
    if rate < 0 or elapsed < 0: raise ValueError("Negative rate/time")
    available = min(Fraction(capacity), tokens + rate*elapsed)
    if demand > capacity: return str(available), "oversized_batch", None
    if available >= demand: return str(available), "fits_projection", "0"
    if rate == 0: return str(available), "no_refill", None
    return str(available), "wait_projection", str((demand-available)/rate)

if __name__ == "__main__":
    for demand in (8,9,11):
        print(demand, budget(10,3,"2","2.5",demand))
    print("capped:", budget(10,3,"2","100",10))
    print("no_refill:", budget(10,3,"0","100",4))
