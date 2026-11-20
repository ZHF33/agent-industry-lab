"""Show how the packing scope changes the number of pallets."""


def pallets(cartons, capacity):
    if type(cartons) is not int or cartons < 0:
        raise ValueError("cartons must be a nonnegative integer")
    if type(capacity) is not int or capacity < 1:
        raise ValueError("capacity must be a positive integer")
    full, remainder = divmod(cartons, capacity)
    return full + int(remainder > 0)


if __name__ == "__main__":
    print("separate", pallets(9, 8) + pallets(7, 8))
    print("pooled", pallets(9 + 7, 8))
    print("exact", pallets(8, 8))
    try:
        pallets(9, 0)
    except ValueError as error:
        print("invalid", error)
