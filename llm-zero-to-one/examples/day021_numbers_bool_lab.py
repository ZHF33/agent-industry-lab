for value in (1, True, 0, None):
    integer_family = isinstance(value, int)
    valid_severity = type(value) is int and 1 <= value <= 3
    print(repr(value), integer_family, valid_severity)

print(0.1 + 0.2 == 0.3)
