import json
import sqlite3
import subprocess
import sys
from pathlib import Path

from services import image_generation_service, image_selection_service

ROOT = Path(__file__).resolve().parents[1]


def make_package(package_dir: Path) -> None:
    package_dir.mkdir(parents=True)
    metadata = {
        "run_id": package_dir.name,
        "status": "approved",
        "approval_status": "approved",
        "product_name": "Black sesame bagel",
        "platform": "xiaohongshu,douyin",
        "content_goal": "Generate image variants.",
        "created_at": "2026-07-02T00:00:00",
        "updated_at": "2026-07-02T00:00:00",
        "content_task": {
            "natural_request": "Create cutaway image",
            "image_type": "cutaway_detail",
            "visual_intent": "cutaway close-up",
        },
        "assets": {"image_generation": {"status": "not_started", "image_paths": [], "review_status": "pending"}},
    }
    prompt = {
        "product_query": "Black sesame bagel",
        "aspect_ratio": "1:1",
        "variants": [
            {"variant_id": "cutaway_detail", "title": "Cutaway", "prompt_en": "cutaway prompt", "status": "prepared"},
            {"variant_id": "hero", "title": "Hero", "prompt_en": "hero prompt", "status": "prepared"},
        ],
    }
    (package_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    (package_dir / "enhanced_image_prompt.json").write_text(json.dumps(prompt, ensure_ascii=False, indent=2), encoding="utf-8")
    (package_dir / "review.md").write_text("# Approval Package\n\n## Manual Notes\n\n- ", encoding="utf-8")
    (package_dir / "product_flow.md").write_text("# Product Operation Flow\n", encoding="utf-8")
    (package_dir / "tasks.json").write_text("[]", encoding="utf-8")
    (package_dir / "assets.json").write_text("[]", encoding="utf-8")


def test_select_image_variant_updates_package_prompt_flow_and_db(tmp_path):
    package_dir = tmp_path / "approval_queue" / "run_select_image"
    out_dir = tmp_path / "generated_images"
    db = tmp_path / "ops.sqlite3"
    make_package(package_dir)

    image_generation_service.generate_for_package(package_dir, out_dir=out_dir, live=False, require_key=False, n=1, db=db)
    result = image_selection_service.select_image_variant(package_dir, "cutaway_detail", note="Use this one.", db=db)

    assert result["status"] == "selected"
    assert result["image_id"] == "cutaway_detail"
    metadata = json.loads((package_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["selected_image_id"] == "cutaway_detail"
    assert metadata["assets"]["image_generation"]["selected_image_id"] == "cutaway_detail"
    assert metadata["assets"]["image_generation"]["images"][0]["review_status"] == "selected"
    assert metadata["assets"]["image_generation"]["images"][1]["review_status"] == "not_selected"

    prompt = json.loads((package_dir / "enhanced_image_prompt.json").read_text(encoding="utf-8"))
    assert prompt["selected_variant_id"] == "cutaway_detail"
    assert prompt["variants"][0]["selected"] is True
    assert prompt["variants"][1]["selected"] is False

    product_flow = (package_dir / "product_flow.md").read_text(encoding="utf-8")
    assert "selected_image_id: cutaway_detail" in product_flow
    assert "selected: True" in product_flow

    with sqlite3.connect(db) as conn:
        selected = conn.execute(
            "SELECT status FROM generated_assets WHERE run_id = ? AND asset_id = ?",
            ("run_select_image", "run_select_image_image_cutaway_detail"),
        ).fetchone()
    assert selected[0] == "selected"


def test_select_image_variant_cli(tmp_path):
    package_dir = tmp_path / "approval_queue" / "run_select_cli"
    out_dir = tmp_path / "generated_images"
    db = tmp_path / "ops.sqlite3"
    make_package(package_dir)
    image_generation_service.generate_for_package(package_dir, out_dir=out_dir, live=False, require_key=False, n=1, db=db)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/select_image_variant.py",
            "--package",
            str(package_dir),
            "--image-id",
            "hero",
            "--note",
            "Hero selected.",
            "--db",
            str(db),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )

    data = json.loads(result.stdout)
    assert data["image_id"] == "hero"
    metadata = json.loads((package_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["selected_image_id"] == "hero"


def test_select_image_variant_rejects_unknown_variant(tmp_path):
    package_dir = tmp_path / "approval_queue" / "run_select_missing"
    db = tmp_path / "ops.sqlite3"
    make_package(package_dir)

    try:
        image_selection_service.select_image_variant(package_dir, "missing", db=db)
    except RuntimeError as exc:
        assert "No generated or prepared image variants" in str(exc)
    else:
        raise AssertionError("Expected missing generated images to fail before selection.")
