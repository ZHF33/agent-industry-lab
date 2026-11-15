def project(previous, current, planned, limit):
    if previous is None or current is None:
        return "missing", None
    if current < previous:
        return "regression", None
    projected = current + planned
    return ("fits" if projected <= limit else "exceeds"), projected


for example in ((80, 90, 10, 100), (80, 90, 11, 100), (88, 5, 4, 100), (20, None, 5, 100)):
    print(*project(*example))
