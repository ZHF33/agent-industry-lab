def decide(previous, current, planned, limit):
    if previous is None or current is None:
        return "missing"
    elif current < previous:
        return "regression"
    elif current + planned > limit:
        return "exceeds"
    else:
        return "fits"


for example in ((80, 90, 10, 100), (80, 90, 11, 100), (88, 5, 4, 100),
                (20, None, 5, 100), (0, 0, 5, 100)):
    print(decide(*example))
