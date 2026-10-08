import json
import sqlite3
import subprocess
import sys
from pathlib import Path

from services import publish_service

ROOT = Path(__file__).resolve().parents[1]


def make_publish_ready_package(tmp_path: Path) -> tuple[Path, Path]:
    package_dir = tmp_path / "approval_queue" / "run_publish_ready"
    package_dir.mkdir(parents=True)
    output = tmp_path / "operations" / "dify_output.json"
    output.parent.mkdir(parents=True)
    output.write_text(
        json.dumps(
            {
                "data": {
                    "outputs": {
                        "content_plan": {"theme": "cutaway bagel feature"},
                        "xiaohongshu_copy": {"title": "Black sesame bagel", "body": "Review-ready copy", "cta": "Manual review first"},
                        "douyin_script": {"hook": "Show the cutaway", "shots": ["cutaway", "counter"], "cta": "Manual review first"},
                        "compliance_result": {"approved": True, "risk_level": "low"},
                    }
                }
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    metadata = {
        "run_id": "run_publish_ready",
        "campaign_id": "campaign_publish",
        "status": "approved",
        "approval_status": "approved",
        "product_name": "Black sesame bagel",
        "platform": "xiaohongshu,douyin",
        "content_goal": "Prepare manual publish draft.",
        "source_output": str(output),
        "created_at": "2026-07-03T00:00:00",
        "updated_at": "2026-07-03T00:00:00",
        "assets": {
            "image_generation": {
                "status": "prepared",
                "review_status": "selected",
                "selected_image_id": "cutaway_detail",
                "selected_image": {
                    "image_id": "cutaway_detail",
                    "provider": "openai",
                    "status": "prepared",
                    "metadata_path": str(tmp_path / "generated_images" / "cutaway.json"),
                    "image_paths": [],
                },
                "images": [
                    {"image_id": "cutaway_detail", "review_status": "selected", "selected": True, "status": "prepared"},
                    {"image_id": "hero", "review_status": "not_selected", "selected": False, "status": "prepared"},
                ],
            }
        },
    }
    prompt = {
        "selected_variant_id": "cutaway_detail",
        "variants": [
            {"variant_id": "cutaway_detail", "selected": True, "review_status": "selected"},
            {"variant_id": "hero", "selected": False, "review_status": "not_selected"},
        ],
    }
    (package_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    (package_dir / "enhanced_image_prompt.json").write_text(json.dumps(prompt, ensure_ascii=False, indent=2), encoding="utf-8")
    (package_dir / "review.md").write_text("# Approval Package\n\n## Manual Notes\n\n- ", encoding="utf-8")
    (package_dir / "product_flow.md").write_text("# Product Operation Flow\n", encoding="utf-8")
    (package_dir / "tasks.json").write_text("[]", encoding="utf-8")
    (package_dir / "assets.json").write_text("[]", encoding="utf-8")
    (package_dir / "revision_requests.json").write_text("[]", encoding="utf-8")
    return package_dir, output


def test_prepare_publish_draft_updates_package_and_db(tmp_path):
    package_dir, _output = make_publish_ready_package(tmp_path)
    db = tmp_path / "ops.sqlite3"
    out_dir = tmp_path / "publish_drafts"

    result = publish_service.prepare_publish_draft(package_dir, out_dir=out_dir, db=db)

    assert result["status"] == "draft_prepared"
    assert result["selected_image_id"] == "cutaway_detail"
    assert Path(result["draft_path"]).exists()
    assert (package_dir / "publish_draft.json").exists()
    assert (package_dir / "publish_draft.md").exists()
    draft = json.loads((package_dir / "publish_draft.json").read_text(encoding="utf-8"))
    assert draft["manual_publish_required"] is True
    assert "xiaohongshu" in draft["platform_drafts"]
    assert "douyin" in draft["platform_drafts"]

    metadata = json.loads((package_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["publish_status"] == "draft_prepared"
    assert metadata["publish_draft_path"].endswith("publish_draft.json")
    product_flow = (package_dir / "product_flow.md").read_text(encoding="utf-8")
    assert "selected_image_id: cutaway_detail" in product_flow
    assert "publish_status: draft_prepared" in product_flow
    assert "publish_draft_path:" in product_flow

    with sqlite3.connect(db) as conn:
        task = conn.execute("SELECT task_type, status FROM tasks WHERE related_run_id = ?", ("run_publish_ready",)).fetchone()
        review = conn.execute("SELECT status FROM approval_reviews WHERE run_id = ?", ("run_publish_ready",)).fetchone()
    assert task == ("manual_publish_record", "succeeded")
    assert review[0] == "publish_draft_prepared"


def test_record_manual_publish_updates_metadata_and_history(tmp_path):
    package_dir, _output = make_publish_ready_package(tmp_path)
    db = tmp_path / "ops.sqlite3"
    publish_service.prepare_publish_draft(package_dir, out_dir=tmp_path / "publish_drafts", db=db)

    result = publish_service.record_manual_publish(
        package_dir,
        platform="xiaohongshu",
        published_url="https://example.com/post/1",
        note="Published manually.",
        metrics={"likes": 12, "saves": 3},
        db=db,
    )

    assert result["status"] == "partially_published"
    assert result["platform"] == "xiaohongshu"
    assert result["published_platforms"] == ["xiaohongshu"]
    assert result["pending_platforms"] == ["douyin"]
    metadata = json.loads((package_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["publish_status"] == "partially_published"
    assert metadata["publish_records"][0]["published_url"] == "https://example.com/post/1"
    assert (package_dir / "publish_record.json").exists()
    with sqlite3.connect(db) as conn:
        history = conn.execute(
            "SELECT platform, likes, saves, conversion_notes FROM campaign_history WHERE run_id = ?",
            ("run_publish_ready",),
        ).fetchone()
    assert history == ("xiaohongshu", 12, 3, "Published manually.")


def test_record_manual_publish_allows_second_platform(tmp_path):
    package_dir, _output = make_publish_ready_package(tmp_path)
    db = tmp_path / "ops.sqlite3"
    publish_service.prepare_publish_draft(package_dir, out_dir=tmp_path / "publish_drafts", db=db)

    first = publish_service.record_manual_publish(
        package_dir,
        platform="xiaohongshu",
        published_url="https://example.com/xhs/1",
        note="XHS published manually.",
        db=db,
    )
    second = publish_service.record_manual_publish(
        package_dir,
        platform="douyin",
        published_url="https://example.com/douyin/1",
        note="Douyin published manually.",
        metrics={"likes": 7},
        db=db,
    )

    assert first["status"] == "partially_published"
    assert second["status"] == "published"
    assert second["published_platforms"] == ["xiaohongshu", "douyin"]
    assert second["pending_platforms"] == []
    metadata = json.loads((package_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["publish_status"] == "published"
    assert len(metadata["publish_records"]) == 2
    with sqlite3.connect(db) as conn:
        history = conn.execute(
            "SELECT platform, likes FROM campaign_history WHERE run_id = ? ORDER BY platform",
            ("run_publish_ready",),
        ).fetchall()
    assert history == [("douyin", 7), ("xiaohongshu", 0)]


def test_prepare_publish_draft_is_idempotent_for_publish_task(tmp_path):
    package_dir, _output = make_publish_ready_package(tmp_path)
    db = tmp_path / "ops.sqlite3"
    out_dir = tmp_path / "publish_drafts"

    first = publish_service.prepare_publish_draft(package_dir, out_dir=out_dir, db=db)
    second = publish_service.prepare_publish_draft(package_dir, out_dir=out_dir, db=db)

    assert second["task_id"] == first["task_id"]
    tasks = json.loads((package_dir / "tasks.json").read_text(encoding="utf-8"))
    publish_tasks = [task for task in tasks if task.get("task_type") == "manual_publish_record"]
    assert len(publish_tasks) == 1
    with sqlite3.connect(db) as conn:
        task_count = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE related_run_id = ? AND task_type = ?",
            ("run_publish_ready", "manual_publish_record"),
        ).fetchone()[0]
    assert task_count == 1


def test_prepare_publish_draft_migrates_legacy_publish_placeholder_task(tmp_path):
    package_dir, _output = make_publish_ready_package(tmp_path)
    db = tmp_path / "ops.sqlite3"
    legacy_task = {
        "task_id": "legacy_publish_task",
        "task_type": "publish_placeholder",
        "status": "pending",
        "provider": "manual",
        "related_run_id": "run_publish_ready",
        "related_package_path": str(package_dir),
        "related_asset_id": "",
        "input_json": {},
        "output_json": {},
        "error_message": "",
        "created_at": "2026-07-03T00:00:00",
        "updated_at": "2026-07-03T00:00:00",
    }
    (package_dir / "tasks.json").write_text(json.dumps([legacy_task], ensure_ascii=False), encoding="utf-8")

    result = publish_service.prepare_publish_draft(package_dir, out_dir=tmp_path / "publish_drafts", db=db)

    assert result["task_id"] == "legacy_publish_task"
    tasks = json.loads((package_dir / "tasks.json").read_text(encoding="utf-8"))
    assert [task["task_type"] for task in tasks] == ["manual_publish_record"]
    with sqlite3.connect(db) as conn:
        db_task_type = conn.execute("SELECT task_type FROM tasks WHERE task_id = ?", ("legacy_publish_task",)).fetchone()[0]
    assert db_task_type == "manual_publish_record"


def test_prepare_publish_draft_cli(tmp_path):
    package_dir, _output = make_publish_ready_package(tmp_path)
    db = tmp_path / "ops.sqlite3"
    out_dir = tmp_path / "publish_drafts"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/prepare_publish_draft.py",
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
    assert data["status"] == "draft_prepared"
    assert data["selected_image_id"] == "cutaway_detail"


def test_record_manual_publish_cli(tmp_path):
    package_dir, _output = make_publish_ready_package(tmp_path)
    db = tmp_path / "ops.sqlite3"
    publish_service.prepare_publish_draft(package_dir, out_dir=tmp_path / "publish_drafts", db=db)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/record_manual_publish.py",
            "--package",
            str(package_dir),
            "--platform",
            "douyin",
            "--url",
            "https://example.com/douyin/1",
            "--note",
            "Published manually.",
            "--likes",
            "5",
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
    assert data["status"] == "partially_published"
    assert data["platform"] == "douyin"


def test_prepare_publish_draft_requires_approval_and_selected_image(tmp_path):
    package_dir, _output = make_publish_ready_package(tmp_path)
    metadata = json.loads((package_dir / "metadata.json").read_text(encoding="utf-8"))
    metadata["approval_status"] = "pending"
    (package_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")

    try:
        publish_service.prepare_publish_draft(package_dir, out_dir=tmp_path / "drafts", db=tmp_path / "ops.sqlite3")
    except RuntimeError as exc:
        assert "requires approved package" in str(exc)
    else:
        raise AssertionError("Expected unapproved package to be rejected.")


def test_prepare_publish_draft_requires_source_outputs(tmp_path):
    package_dir, _output = make_publish_ready_package(tmp_path)
    metadata = json.loads((package_dir / "metadata.json").read_text(encoding="utf-8"))
    metadata["source_output"] = str(tmp_path / "missing_output.json")
    (package_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")

    try:
        publish_service.prepare_publish_draft(package_dir, out_dir=tmp_path / "drafts", db=tmp_path / "ops.sqlite3")
    except RuntimeError as exc:
        assert "source output is missing or empty" in str(exc)
    else:
        raise AssertionError("Expected missing source output to be rejected.")


def test_prepare_publish_draft_requires_valid_selected_image(tmp_path):
    package_dir, _output = make_publish_ready_package(tmp_path)
    metadata = json.loads((package_dir / "metadata.json").read_text(encoding="utf-8"))
    metadata["assets"]["image_generation"]["selected_image"] = {}
    metadata["assets"]["image_generation"]["images"] = []
    (package_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")

    try:
        publish_service.prepare_publish_draft(package_dir, out_dir=tmp_path / "drafts", db=tmp_path / "ops.sqlite3")
    except RuntimeError as exc:
        assert "requires selected image details" in str(exc)
    else:
        raise AssertionError("Expected invalid selected image metadata to be rejected.")
