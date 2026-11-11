expected = "001236"
for scan in ("001236", "001235", "001243"):
    weighted = sum(int(digit) * weight for digit, weight in zip(scan[:-1], (3, 1, 3, 1, 3)))
    valid = (weighted + int(scan[-1])) % 10 == 0
    print(valid, scan == expected)
