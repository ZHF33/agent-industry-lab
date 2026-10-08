import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_generate_openai_image_dry_run(tmp_path):
    prompt_file = tmp_path / "image_prompt.json"
    out_dir = tmp_path / "generated_images"
    prompt_file.write_text(
        json.dumps(
            {
                "enhanced_prompt_en": "1:1 image, unbranded milk tea, no embedded text",
                "negative_prompt": "logo, brand name, trademark",
                "compliance_rules": ["Use an unbranded cup and avoid any visible text."],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/generate_openai_image.py",
            "--input",
            str(prompt_file),
            "--out-dir",
            str(out_dir),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    report = json.loads(result.stdout)
    assert report["mode"] == "dry_run"
    assert report["status"] == "prepared"
    metadata = json.loads(Path(report["metadata_path"]).read_text(encoding="utf-8"))
    assert metadata["request_payload"]["model"]
    assert "no embedded text" in metadata["request_payload"]["prompt"]
    assert "logo" in metadata["request_payload"]["prompt"]


def test_generate_openai_image_updates_approval_package(tmp_path):
    prompt_file = tmp_path / "image_prompt.json"
    out_dir = tmp_path / "generated_images"
    package_dir = tmp_path / "approval_queue" / "chagee_test"
    package_dir.mkdir(parents=True)
    (package_dir / "metadata.json").write_text(
        json.dumps(
            {
                "status": "approved",
                "approval_status": "approved",
                "assets": {
                    "image_generation": {
                        "status": "not_started",
                        "metadata_path": "",
                        "image_paths": [],
                        "review_status": "pending",
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (package_dir / "review.md").write_text(
        "# Approval Package\n\n## Generated Assets\n\n- Image generation: not_started\n\n## Review Checklist\n\n- [ ] check image\n",
        encoding="utf-8",
    )
    prompt_file.write_text(
        json.dumps(
            {
                "enhanced_prompt_en": "1:1 image, unbranded milk tea, no embedded text",
                "negative_prompt": "logo, brand name, trademark",
                "compliance_rules": ["Use an unbranded cup and avoid any visible text."],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            "scripts/generate_openai_image.py",
            "--input",
            str(prompt_file),
            "--out-dir",
            str(out_dir),
            "--approval-package",
            str(package_dir),
        ],
        cwd=ROOT,
        check=True,
    )

    metadata = json.loads((package_dir / "metadata.json").read_text(encoding="utf-8"))
    image_generation = metadata["assets"]["image_generation"]
    assert image_generation["status"] == "prepared"
    assert image_generation["mode"] == "dry_run"
    assert image_generation["review_status"] == "pending"
    review = (package_dir / "review.md").read_text(encoding="utf-8")
    assert "Image generation status: prepared" in review
    assert "Image metadata:" in review


def test_generate_openai_image_rejects_unapproved_backfill(tmp_path):
    prompt_file = tmp_path / "image_prompt.json"
    out_dir = tmp_path / "generated_images"
    package_dir = tmp_path / "approval_queue" / "run_pending"
    package_dir.mkdir(parents=True)
    (package_dir / "metadata.json").write_text(
        json.dumps({"status": "pending", "approval_status": "pending", "assets": {"image_generation": {"status": "not_started"}}}),
        encoding="utf-8",
    )
    (package_dir / "review.md").write_text("# Approval Package\n", encoding="utf-8")
    prompt_file.write_text(json.dumps({"enhanced_prompt_en": "1:1 image, unbranded bread"}, ensure_ascii=False), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/generate_openai_image.py",
            "--input",
            str(prompt_file),
            "--out-dir",
            str(out_dir),
            "--approval-package",
            str(package_dir),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "only backfill approved packages" in result.stderr
