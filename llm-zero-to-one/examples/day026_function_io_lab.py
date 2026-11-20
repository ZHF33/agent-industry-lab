"""Compare returning a load value with printing it."""


def load_units(boxes, units_per_box):
    return boxes * units_per_box


def show_load_units(boxes, units_per_box):
    print("displayed", boxes * units_per_box)


if __name__ == "__main__":
    load = load_units(3, 4)
    print("returned", load)
    print("combined", load + load_units(1, 4))
    result = show_load_units(3, 4)
    print("display function returned", result)
