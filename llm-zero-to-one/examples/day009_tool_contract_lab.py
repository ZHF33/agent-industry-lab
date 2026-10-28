"""Scripted pure-tool contract; no model, network, eval or writes."""

def compare_revision(arguments):
    if not isinstance(arguments, dict) or set(arguments) != {"base", "current"}:
        raise ValueError("Exactly base and current required")
    if any(type(value) is not int or value < 1 for value in arguments.values()):
        raise ValueError("Positive integer revisions required")
    return {"matches": arguments["base"] == arguments["current"], "write_authorized": False}


def dispatch(call):
    if not isinstance(call, dict) or set(call) != {"name", "arguments"}:
        return {"error": "invalid_call"}
    if call["name"] != "compare_revision":
        return {"error": "tool_not_allowed"}
    try:
        return compare_revision(call["arguments"])
    except ValueError as error:
        return {"error": str(error)}


if __name__ == "__main__":
    cases = [
        {"name": "compare_revision", "arguments": {"base": 4, "current": 5}},
        {"name": "compare_revision", "arguments": {"base": "4", "current": 5}},
        {"name": "compare_revision", "arguments": {"base": 5, "current": 5}},
        {"name": "update_record", "arguments": {"base": 5, "current": 5}},
    ]
    for case in cases: print(dispatch(case))
