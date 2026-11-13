limit = 5
for error, uncertainty in ((3, 2), (4, 2), (-7, 1)):
    low, high = error - uncertainty, error + uncertainty
    if low >= -limit and high <= limit:
        status = "inside"
    elif low > limit or high < -limit:
        status = "outside"
    else:
        status = "overlaps_limit"
    print(low, high, status)
