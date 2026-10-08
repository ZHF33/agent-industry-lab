import json
from pathlib import Path

from services import approval_service


def test_approval_service_create_and_validate(tmp_path):
    dify = tmp_path / "dify.json"
    prompt = tmp_path / "prompt.json"
    dify.write_text(json.dumps({"data": {"outputs": {"content_plan": {"theme": "test"}}}}, ensure_ascii=False), encoding="utf-8")
    prompt.write_text(json.dumps({"enhanced_prompt_en": "unbranded tea"}, ensure_ascii=False), encoding="utf-8")
    result = approval_service.create_approval_package(dify, prompt, tmp_path / "queue")
    assert approval_service.validate_approval_package(result["package_dir"])
    package = approval_service.load_approval_package(result["package_dir"])
    assert package["metadata"]["run_id"].startswith("run_")
    assert Path(result["product_flow"]).exists()


def test_approval_service_status_and_backfill(tmp_path):
    dify = tmp_path / "dify.json"
    prompt = tmp_path / "prompt.json"
    dify.write_text(json.dumps({"data": {"outputs": {}}}), encoding="utf-8")
    prompt.write_text(json.dumps({}), encoding="utf-8")
    result = approval_service.create_approval_package(dify, prompt, tmp_path / "queue")
    approval_service.update_approval_status(result["package_dir"], "needs_revision", "改 CTA")
    approval_service.backfill_asset_result(result["package_dir"], "image", {"status": "prepared", "provider": "openai"})
    package = approval_service.load_approval_package(result["package_dir"])
    assert package["metadata"]["approval_status"] == "needs_revision"
    assert package["metadata"]["image_status"] == "prepared"
    product_flow = (Path(result["package_dir"]) / "product_flow.md").read_text(encoding="utf-8")
    assert "approval_status: needs_revision" in product_flow
    assert "asset_status: prepared" in product_flow


def test_create_approval_package_uses_unique_run_dir_for_same_second(tmp_path, monkeypatch):
    dify = tmp_path / "dify.json"
    prompt = tmp_path / "prompt.json"
    out_dir = tmp_path / "queue"
    dify.write_text(
        json.dumps(
            {
                "data": {
                    "outputs": {
                        "content_plan": {"theme": "test"},
                        "xiaohongshu_copy": {"title": "test"},
                        "douyin_script": {"hook": "test"},
                        "video_prompt": {"scene": "test"},
                        "compliance_result": {"risk_level": "low"},
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    prompt.write_text(json.dumps({"enhanced_prompt_en": "unbranded tea"}, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(approval_service, "timestamp", lambda: "20260702_010101")

    first = approval_service.create_approval_package(dify, prompt, out_dir)
    second = approval_service.create_approval_package(dify, prompt, out_dir)

    assert Path(first["package_dir"]).name == "run_20260702_010101"
    assert Path(second["package_dir"]).name == "run_20260702_010101_01"


def test_product_flow_includes_content_task_and_variants(tmp_path):
    dify = tmp_path / "dify.json"
    prompt = tmp_path / "prompt.json"
    dify.write_text(
        json.dumps(
            {
                "data": {
                    "outputs": {
                        "content_plan": {"theme": "best seller"},
                        "xiaohongshu_copy": {"title": "Beef ciabatta"},
                        "douyin_script": {"hook": "show the layers"},
                        "compliance_result": {"risk_level": "low"},
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    prompt.write_text(
        json.dumps(
            {
                "product_query": "Beef ciabatta",
                "aspect_ratio": "1:1",
                "variants": [
                    {"variant_id": "hero", "title": "Hero", "status": "prepared", "aspect_ratio": "1:1", "prompt_en": "hero prompt"}
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = approval_service.create_approval_package(
        dify,
        prompt,
        tmp_path / "queue",
        product_name="Beef ciabatta",
        content_task={
            "natural_request": "Today promote Beef ciabatta",
            "content_type": "best_seller_feature",
            "image_type": "deconstructed_exploded_view",
            "visual_intent": "exploded-view display",
        },
    )

    product_flow = (Path(result["package_dir"]) / "product_flow.md").read_text(encoding="utf-8")
    assert "Today promote Beef ciabatta" in product_flow
    assert "visual_intent: exploded-view display" in product_flow
    assert "variant_count: 1" in product_flow
    assert "hero prompt" in product_flow
