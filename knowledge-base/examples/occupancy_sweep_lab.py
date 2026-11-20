"""Count concurrent reservations between adjacent time boundaries."""
from collections import Counter


def occupancy(bookings, capacity):
    changes = Counter()
    for start, end in bookings:
        if not start < end:
            raise ValueError("start must precede end")
        changes[start] += 1
        changes[end] -= 1

    times = sorted(changes)
    peak = active = 0
    conflicts = []
    for start, end in zip(times, times[1:]):
        active += changes[start]
        peak = max(active, peak)
        if active > capacity:
            conflicts.append((start, end, active - capacity))
    return peak, conflicts


if __name__ == "__main__":
    bookings = [(0, 60), (15, 75), (30, 60), (60, 90)]
    for capacity in (2, 3):
        peak, conflicts = occupancy(bookings, capacity)
        print(f"capacity={capacity} peak={peak} conflicts={conflicts}")
