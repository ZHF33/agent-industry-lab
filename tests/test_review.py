from fastapi.testclient import TestClient
from industry_lab.api import create_app
import pytest


def task(job_id="demo"):
    return {"job_id": job_id, "product": {"name": "Beef ciabatta", "facts": {"ingredients": "beef, wheat", "storage": "refrigerate"}}, "claims": [{"text": "Made with beef", "fact_key": "ingredients", "fact_value": "beef, wheat"}], "copy": "Beef ciabatta", "max_chars": 100}


def test_review_is_gated_and_idempotent(tmp_path):
    with TestClient(create_app(tmp_path / "ops.sqlite3")) as client:
        first = client.post("/reviews", json=task())
        assert first.status_code == 200
        assert first.json()["status"] == "pending_review"
        assert client.post("/reviews", json=task()).json() == first.json()
        changed = task(); changed["copy"] = "different"
        assert client.post("/reviews", json=changed).status_code == 409
        assert client.post("/reviews/demo/decision", json={"decision": "approved", "reviewer": "operator", "note": "Facts and full copy checked"}).json()["status"] == "approved"


def test_unknown_evidence_and_missing_facts_block_approval(tmp_path):
    with TestClient(create_app(tmp_path / "ops.sqlite3")) as client:
        body = task(); body["product"]["facts"].pop("storage")
        body["claims"][0]["fact_value"] = "no allergens"
        result = client.post("/reviews", json=body).json()
        assert {i["code"] for i in result["issues"]} == {"missing_fact", "evidence_mismatch"}
        assert client.post("/reviews/demo/decision", json={"decision": "approved", "reviewer": "operator", "note": "ok"}).status_code == 422


def test_undeclared_claims_always_require_human_review(tmp_path):
    with TestClient(create_app(tmp_path / "ops.sqlite3")) as client:
        body = task(); body["copy"] = "Guaranteed health benefits"; body["claims"] = []
        result = client.post("/reviews", json=body).json()
        assert result["status"] == "pending_review"
        assert result["semantic_verified"] is False
        assert "full copy" in result["human_checks"][0]


def test_limits_and_missing_job(tmp_path):
    with TestClient(create_app(tmp_path / "ops.sqlite3")) as client:
        body = task(); body["max_chars"] = 3
        assert client.post("/reviews", json=body).json()["issues"][0]["code"] == "channel_limit"
        assert client.get("/reviews/unknown").status_code == 404
        body["job_id"] = "../bad"
        assert client.post("/reviews", json=body).status_code == 422


@pytest.mark.parametrize("key", ["ingredients", "storage"])
@pytest.mark.parametrize("value", ["", " ", None])
def test_required_product_facts(tmp_path, key, value):
    body = task()
    if value is None:
        body["product"]["facts"].pop(key)
    else:
        body["product"]["facts"][key] = value
    with TestClient(create_app(tmp_path / "ops.sqlite3")) as client:
        assert any(i["code"] == "missing_fact" for i in client.post("/reviews", json=body).json()["issues"])


def test_decision_survives_restart_and_cannot_be_overwritten(tmp_path):
    path = tmp_path / "ops.sqlite3"
    with TestClient(create_app(path)) as client:
        client.post("/reviews", json=task())
        assert client.post("/reviews/demo/decision", json={"decision": "rejected", "reviewer": "operator", "note": "revise"}).status_code == 200
    with TestClient(create_app(path)) as client:
        assert client.get("/reviews/demo").json()["status"] == "rejected"
        assert client.post("/reviews/demo/decision", json={"decision": "approved", "reviewer": "operator", "note": "overwrite"}).status_code == 409
