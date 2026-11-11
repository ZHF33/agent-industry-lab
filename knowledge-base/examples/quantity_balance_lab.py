"""Synthetic quantity arithmetic; no external I/O."""
requested = 10
records = [
    {"record_id": "M1", "direction": "issue", "quantity": 8},
    {"record_id": "M2", "direction": "return", "quantity": 1},
]
issued = sum(row["quantity"] for row in records if row["direction"] == "issue")
returned = sum(row["quantity"] for row in records if row["direction"] == "return")
net = issued - returned
print(f"requested={requested} issued={issued} returned={returned} net={net} difference={net-requested}")
print("records=" + ",".join(row["record_id"] for row in records))
print(f"returned={returned+1} difference={issued-(returned+1)-requested}")
