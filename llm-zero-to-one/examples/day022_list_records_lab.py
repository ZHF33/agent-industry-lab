first_batch = [("P10", 10003), ("P20", 20004)]
next_batch = [("P30", 29993), ("P40", 40001)]
grouped = first_batch.copy()
grouped.append(next_batch)
records = first_batch.copy()
records.extend(next_batch)

print(len(grouped), len(records))
for point, reading in records:
    print(point, reading)
