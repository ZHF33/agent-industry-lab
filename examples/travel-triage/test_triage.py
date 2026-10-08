import copy
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("travel_triage", Path(__file__).with_name("triage.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixture(kind, index):
    doc = {"document_id": "synthetic-doc", "kind": "itinerary", "pnr": "DEMO01", "passenger_name": "Demo Traveler", "sha256": "a" * 64}
    case = {"case_id": f"demo-{kind}-{index}", "pnr": "DEMO01", "passenger_name": "Demo Traveler", "documents": [doc]}
    if kind == "normal":
        doc["passenger_name"] = "  DEMO   traveler "
    elif kind == "missing_itinerary":
        case["documents"] = []
    elif kind == "name_mismatch":
        doc["passenger_name"] = "Other Traveler"
    elif kind == "duplicate_document":
        case["documents"].append({**doc, "kind": "attachment"})
    elif kind == "multiple_candidates":
        case["documents"].append({**doc, "sha256": "b" * 64})
    elif kind == "insufficient_information":
        doc["passenger_name"] = None
    return case


@pytest.mark.parametrize("kind", ["normal", "missing_itinerary", "name_mismatch", "duplicate_document", "multiple_candidates", "insufficient_information"])
@pytest.mark.parametrize("index", [1, 2])
def test_synthetic_cases(kind, index):
    case = fixture(kind, index)
    original = copy.deepcopy(case)
    result = module.triage(case)
    types = {i["type"] for i in result["issues"]}
    assert types == (set() if kind == "normal" else {kind})
    assert case == original
    assert result["human_review_required"] and not result["travel_approved"]
    assert all(i["source"] for i in result["issues"])


def test_model_bound_and_mandatory_fallback():
    calls = []
    def model(messages):
        calls.append(1)
        return {"role": "assistant", "tool_calls": [{"function": {"name": "unknown"}}]}
    result = module.triage(fixture("name_mismatch", 1), model)
    assert len(calls) == result["model_rounds"] == 3
    assert result["issues"][0]["type"] == "name_mismatch"
    assert all(t["fallback"] for t in result["tool_trace"])


def test_tool_evidence_ignores_model_claims():
    def model(messages):
        return {"role": "assistant", "content": "Everything approved", "tool_calls": [{"function": {"name": n}} for n in module.TOOLS]}
    result = module.triage(fixture("missing_itinerary", 1), model)
    assert result["status"] == "needs_review" and result["model_rounds"] == 1


def test_bad_input():
    with pytest.raises(ValueError):
        module.triage({"case_id": "demo", "documents": [{"sha256": "not-a-hash"}]})


def test_unknown_association_never_passes():
    case = fixture("normal", 1)
    case["documents"][0]["pnr"] = None
    assert module.triage(case)["issues"][0]["type"] == "insufficient_information"
