"""Offline contract experiments using the existing project model."""
import sys
from pathlib import Path
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from industry_lab.api import ReviewInput, review

payload = {"job_id": "contract-demo", "product": {"name": "Demo Bread", "facts": {"ingredients": "flour", "storage": "cool"}}, "claims": [], "copy": "Demo", "max_chars": 100}
model = ReviewInput.model_validate(payload)
assert model.content == "Demo"
assert model.model_dump()["content"] == "Demo"
assert model.model_dump(by_alias=True)["copy"] == "Demo"
print("PASS: external copy maps to internal content; explicit aliases control output")
for change in ({"job_id": "../invalid"}, {"max_chars": 0}, {"copy": ""}):
    try:
        ReviewInput.model_validate({**payload, **change})
    except ValidationError:
        pass
    else:
        raise AssertionError("invalid input unexpectedly accepted")
print("PASS: invalid ID, range and empty copy rejected")
converted = ReviewInput.model_validate({**payload, "max_chars": "100"})
assert converted.max_chars == 100
try:
    ReviewInput.model_validate({**payload, "max_chars": "100"}, strict=True)
except ValidationError:
    pass
else:
    raise AssertionError("strict validation accepted a numeric string")
print("PASS: default conversion and strict rejection differ")
extra = ReviewInput.model_validate({**payload, "unrecognized": "demo"})
assert "unrecognized" not in extra.model_dump()
assert review(model)["semantic_verified"] is False
print("PASS: extra field ignored by current model; valid structure does not imply semantic truth")
