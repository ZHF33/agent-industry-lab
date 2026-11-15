records = [
    {"point": "rack", "state": "clear"},
    {"point": "rack", "state": "residue"},
    {"point": "bin", "state": None},
]
latest_value, grouped = {}, {}
for record in records:
    point = record["point"]
    state = record["state"]
    latest_value[point] = state
    grouped.setdefault(point, []).append(state)

print(latest_value["rack"])
print(grouped["rack"])
for record in (records[-1], {"point": "table"}):
    if "state" not in record:
        print("missing key")
    elif record["state"] is None:
        print("missing value")
