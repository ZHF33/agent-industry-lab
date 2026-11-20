"""Calculate complete kits from synthetic dedicated stock."""


def capacity(available, per_unit):
    supports = []
    for material, required in per_unit.items():
        if material not in available:
            return None
        supports.append(available[material] // required)
    return min(supports)


if __name__ == "__main__":
    bom = {"BODY": 1, "BOLT": 2, "SEAL": 1}
    for label, stock in (
        ("zero", {"BODY": 10, "BOLT": 19, "SEAL": 0}),
        ("replenished", {"BODY": 10, "BOLT": 19, "SEAL": 10}),
        ("missing", {"BODY": 10, "BOLT": 19}),
    ):
        print(label, capacity(stock, bom))
