"""Scripted tool dispatch over fixed fixtures, NOT a model or live network."""
FIXTURE = {"source": "fixture-availability-01", "service_id": "DEMO-SERVICE",
           "value": "maintenance_scheduled", "observed_at": "2026-10-27T12:00:00+00:00"}

def dispatch(message):
    call = message.get("tool_call")
    if call is None:
        return {"status": "no_tool", "network_executed": False}
    if not isinstance(call, dict) or set(call) != {"name", "arguments"}:
        raise ValueError("Invalid call shape")
    if call["name"] != "lookup_fixture" or call["arguments"] != {"service_id": "DEMO-SERVICE"}:
        return {"status": "denied", "network_executed": False}
    return {"status": "fixture_read", "network_executed": False, "result": dict(FIXTURE)}

if __name__ == "__main__":
    messages = [
        {"content": "I searched the internet."},
        {"tool_call": {"name": "lookup_fixture", "arguments": {"service_id": "DEMO-SERVICE"}}},
        {"tool_call": {"name": "fetch_any_url", "arguments": {"url": "https://example.invalid"}}},
    ]
    for message in messages:
        result = dispatch(message)
        print(result["status"], "network=", result["network_executed"])
        if "result" in result: print("source:", result["result"]["source"])
