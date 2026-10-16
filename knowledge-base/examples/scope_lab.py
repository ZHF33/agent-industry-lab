def scope(expected, arguments):
    if not isinstance(arguments, dict) or set(arguments) != {"return_id"} or arguments["return_id"] != expected:
        raise ValueError("Invalid tool scope")
    return "allowed"


if __name__ == "__main__":
    print(scope("RET-DEMO-01", {"return_id": "RET-DEMO-01"}))
    try:
        scope("RET-DEMO-01", {"return_id": "other"})
    except ValueError:
        print("rejected")
