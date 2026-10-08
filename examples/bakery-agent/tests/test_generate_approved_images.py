import json
import sqlite3
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def make_approved_image_package(package_dir: Path, status: str = "approved") -> None:
    package_dir.mkdir(parents=True)
    (package_dir / "metadata.json").write_text(
        json.dumps(
            {
                "run_id": package_dir.name,
                "status": status,
                "approval_status": status,
                "product_name": "牛肉恰巴塔",
                "platform": "xiaohongshu,douyin",
                "created_at": "2026-07-01T00:00:00",
                "updated_at": "2026-07-01T00:00:00",
                "assets": {"image_generation": {"status": "not_started", "image_paths": [], "review_status": "pending"}},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (package_dir / "enhanced_image_prompt.json").write_text(
        json.dumps(
            {
                "variants": [
                    {
                        "variant_id": "hero",
                        "enhanced_prompt_en": "1:1 realistic unbranded beef ciabatta product photo, no embedded text",
                    },
                    {
                        "variant_id": "deconstructed",
                        "enhanced_prompt_en": "1:1 deconstructed exploded-view beef ciabatta, ingredients separated, no logos",
                    },
                ],
                "negative_prompt": "logo, trademark, brand name, embedded text",
                "compliance_rules": ["No health claims or fake sales claims."],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (package_dir / "review.md").write_text("# Approval Package\n\n## Review Checklist\n\n- [ ] check image\n", encoding="utf-8")
    (package_dir / "tasks.json").write_text("[]", encoding="utf-8")
    (package_dir / "assets.json").write_text("[]", encoding="utf-8")


def test_generate_approved_images_dry_run_updates_package_and_db(tmp_path):
    package_dir = tmp_path / "approval_queue" / "run_image_ready"
    out_dir = tmp_path / "generated_images"
    db = tmp_path / "ops.sqlite3"
    make_approved_image_package(package_dir)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/generate_approved_images.py",
            "--package",
            str(package_dir),
            "--out-dir",
            str(out_dir),
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
    assert data["ok"] is True
    assert data["approval_status"] == "approved"
    assert data["image_generation"]["status"] == "prepared"
    assert data["image_generation"]["mode"] == "dry_run"
    assert data["image_generation"]["image_count"] == 2

    metadata = json.loads((package_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["assets"]["image_generation"]["status"] == "prepared"
    assert len(metadata["assets"]["image_generation"]["images"]) == 2
    with sqlite3.connect(db) as conn:
        asset_count = conn.execute("SELECT COUNT(*) FROM generated_assets WHERE run_id = ?", ("run_image_ready",)).fetchone()[0]
    assert asset_count == 2


def test_generate_approved_images_local_demo_writes_image_files(tmp_path):
    package_dir = tmp_path / "approval_queue" / "run_image_demo"
    out_dir = tmp_path / "generated_images"
    db = tmp_path / "ops.sqlite3"
    make_approved_image_package(package_dir)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/generate_approved_images.py",
            "--package",
            str(package_dir),
            "--out-dir",
            str(out_dir),
            "--db",
            str(db),
            "--local-demo",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )

    data = json.loads(result.stdout)
    assert data["ok"] is True
    assert data["mode"] == "local_demo"
    assert data["image_generation"]["status"] == "completed"
    metadata = json.loads((package_dir / "metadata.json").read_text(encoding="utf-8"))
    images = metadata["assets"]["image_generation"]["images"]
    assert len(images) == 2
    assert all(image["image_paths"] for image in images)
    assert Path(images[0]["image_paths"][0]).read_bytes().startswith(b"\x89PNG")
    with sqlite3.connect(db) as conn:
        selected = conn.execute("SELECT COUNT(*) FROM generated_assets WHERE run_id = ? AND local_path <> ''", ("run_image_demo",)).fetchone()[0]
    assert selected == 2


def test_generate_approved_images_rejects_unapproved_package(tmp_path):
    package_dir = tmp_path / "approval_queue" / "run_image_pending"
    make_approved_image_package(package_dir, status="pending")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/generate_approved_images.py",
            "--package",
            str(package_dir),
            "--out-dir",
            str(tmp_path / "generated_images"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    assert result.returncode != 0
    assert "requires approved package status" in result.stderr


def test_generate_approved_images_records_live_failure(tmp_path, monkeypatch):
    from services import image_generation_service

    package_dir = tmp_path / "approval_queue" / "run_image_live_failure"
    out_dir = tmp_path / "generated_images"
    db = tmp_path / "ops.sqlite3"
    make_approved_image_package(package_dir)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(image_generation_service.image_service, "load_dotenv", lambda path=".env": {})

    result = image_generation_service.generate_for_package(
        package_dir,
        out_dir=out_dir,
        live=True,
        require_key=True,
        n=1,
        db=db,
        raise_on_failure=False,
    )

    assert result["ok"] is False
    assert result["image_generation"]["status"] == "failed"
    assert "OPENAI_API_KEY is required" in result["error"]
    metadata = json.loads((package_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["image_status"] == "failed"
    assert metadata["assets"]["image_generation"]["error_message"]
    with sqlite3.connect(db) as conn:
        asset = conn.execute("SELECT status, error_message FROM generated_assets WHERE run_id = ?", ("run_image_live_failure",)).fetchone()
    assert asset[0] == "failed"
    assert "OPENAI_API_KEY is required" in asset[1]
