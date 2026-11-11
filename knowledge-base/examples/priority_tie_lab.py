def order(jobs):
    ordered = sorted(jobs, key=lambda row: (-row[1], row[2], row[0]))
    return " ".join(row[0] for row in ordered)


jobs = [("A", 1, 14), ("B", 2, 16), ("C", 2, 16)]
print(order(jobs))
print(order(reversed(jobs)))
print(order([("A", 2, 14), *jobs[1:]]))
