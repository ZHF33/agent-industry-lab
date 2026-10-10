import pytest
from agent import execute, run

TICKET = {"ticket_id": "T", "equipment_id": "EQ-DEMO-01", "description": "vibration"}


def test_control_loop():
    def model(messages):
        if messages[-1]["role"] == "tool":
            return {"role": "assistant", "content": "asset-demo-01：请人工审核"}
        return {"role": "assistant", "tool_calls": [{"function": {"name": "lookup_equipment", "arguments": {"equipment_id": "EQ-DEMO-01"}}}]}
    result = run(TICKET, model)
    assert result["model_rounds"] == 2
    assert result["actions_executed"] is False


@pytest.mark.parametrize("name,args", [("restart", {"equipment_id": "EQ-DEMO-01"}), ("lookup_equipment", {"equipment_id": "other"}), ("lookup_equipment", {})])
def test_reject_tools(name, args):
    with pytest.raises(ValueError):
        execute(name, args, "EQ-DEMO-01")


def test_no_tools():
    with pytest.raises(ValueError):
        run(TICKET, lambda _: {"content": "done"})


def test_limit():
    with pytest.raises(RuntimeError):
        run(TICKET, lambda _: {"tool_calls": [{"function": {"name": "lookup_history", "arguments": {"equipment_id": "EQ-DEMO-01"}}}]})


def test_invalid_input():
    with pytest.raises(ValueError):
        run({})


def test_missing_citation():
    def model(messages):
        if any(message.get("role") == "tool" for message in messages):
            return {"content": "uncited advice"}
        return {"tool_calls": [{"function": {"name": "lookup_equipment", "arguments": {"equipment_id": "EQ-DEMO-01"}}}]}
    with pytest.raises(ValueError):
        run(TICKET, model)
