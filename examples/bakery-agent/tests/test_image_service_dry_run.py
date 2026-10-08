import json

from services import image_service


def test_image_service_build_request():
    request = image_service.build_openai_image_request({"enhanced_prompt_en": "unbranded tea", "negative_prompt": "logo"})
    assert request["model"] == "gpt-image-2"
    assert "logo" in request["prompt"]


def test_image_service_dry_run(tmp_path):
    prompt = tmp_path / "prompt.json"
    prompt.write_text(json.dumps({"enhanced_prompt_en": "unbranded tea"}), encoding="utf-8")
    report = image_service.dry_run_openai_image(prompt, tmp_path / "images")
    assert report["status"] == "prepared"
    assert report["mode"] == "dry_run"


def test_image_service_local_demo_writes_png(tmp_path):
    prompt = tmp_path / "prompt.json"
    prompt.write_text(
        json.dumps(
            {
                "variants": [
                    {"variant_id": "deconstructed", "enhanced_prompt_en": "deconstructed beef ciabatta"},
                    {"variant_id": "hero", "enhanced_prompt_en": "hero beef ciabatta"},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    report = image_service.local_demo_images(prompt, tmp_path / "images", size="256x256")

    assert report["status"] == "completed"
    assert report["mode"] == "local_demo"
    assert len(report["images"]) == 2
    for image in report["images"]:
        assert image["image_paths"]
        image_path = image["image_paths"][0]
        assert image_path.endswith(".png")
        assert open(image_path, "rb").read(8) == b"\x89PNG\r\n\x1a\n"


def test_live_image_readiness_reports_missing_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AGENT_API_ALLOW_LIVE_IMAGE", raising=False)
    monkeypatch.setattr(image_service, "load_dotenv", lambda path=".env": {})
    report = image_service.live_image_readiness(require_agent_api_allow=True)
    assert report["ready"] is False
    assert "OPENAI_API_KEY is missing" in report["blockers"]
    assert "AGENT_API_ALLOW_LIVE_IMAGE is not enabled" in report["blockers"]
    assert report["model"]
