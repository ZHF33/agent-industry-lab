import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_run_content_operation_dry_run(tmp_path):
    db = tmp_path / "ops.sqlite3"
    out_dir = tmp_path / "operations"
    approval_dir = tmp_path / "approval_queue"
    image_dir = tmp_path / "generated_images"
    archive_dir = tmp_path / "operation_archive"
    log_path = tmp_path / "operation_log.jsonl"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_content_operation.py",
            "--mode",
            "dry-run",
            "--db",
            str(db),
            "--out-dir",
            str(out_dir),
            "--approval-out-dir",
            str(approval_dir),
            "--image-out-dir",
            str(image_dir),
            "--archive-out-dir",
            str(archive_dir),
            "--log",
            str(log_path),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    summary = json.loads(result.stdout)
    package_dir = Path(summary["approval_package"])
    assert summary["status"] == "completed"
    assert (package_dir / "metadata.json").exists()
    assert Path(summary["operation_archive"]).exists()
    assert Path(summary["image_metadata"]).exists()
    assert log_path.exists()

    metadata = json.loads((package_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["approval_status"] == "pending"
    assert metadata["db_sync_status"] == "synced"
    assert metadata["image_status"] == "prepared"


def test_query_ops_status_json(tmp_path):
    db = tmp_path / "ops.sqlite3"
    subprocess.run(
        [
            sys.executable,
            "scripts/run_content_operation.py",
            "--mode",
            "dry-run",
            "--db",
            str(db),
            "--out-dir",
            str(tmp_path / "operations"),
            "--approval-out-dir",
            str(tmp_path / "approval_queue"),
            "--image-out-dir",
            str(tmp_path / "generated_images"),
            "--archive-out-dir",
            str(tmp_path / "operation_archive"),
            "--log",
            str(tmp_path / "operation_log.jsonl"),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, "scripts/query_ops_status.py", "--db", str(db), "--latest", "--limit", "1"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    status = json.loads(result.stdout)
    assert status["latest_runs"][0]["approval_status"] == "pending"


def test_query_ops_status_by_run_id_includes_assets_and_reviews(tmp_path):
    from services import db_service, operation_log_service

    db = tmp_path / "ops.sqlite3"
    log_path = tmp_path / "operation_log.jsonl"
    with db_service.get_connection(db) as conn:
        db_service.upsert_content_run(
            conn,
            {
                "run_id": "run_status_detail",
                "product_name": "牛肉恰巴塔",
                "platform": "xiaohongshu",
                "approval_status": "approved",
                "package_path": "runs/approval_queue/run_status_detail",
                "created_at": "2026-07-02T00:00:00",
                "updated_at": "2026-07-02T00:01:00",
            },
        )
        db_service.upsert_asset(
            conn,
            {
                "asset_id": "asset_status_detail",
                "run_id": "run_status_detail",
                "asset_type": "image",
                "provider": "openai",
                "status": "prepared",
                "created_at": "2026-07-02T00:00:00",
                "updated_at": "2026-07-02T00:01:00",
            },
        )
        db_service.upsert_approval_review(
            conn,
            {
                "review_id": "review_status_detail",
                "run_id": "run_status_detail",
                "package_path": "runs/approval_queue/run_status_detail",
                "status": "approved",
                "reviewer_note": "Approved.",
                "created_at": "2026-07-02T00:00:00",
                "updated_at": "2026-07-02T00:01:00",
            },
        )
    operation_log_service.append_event("operation_completed", {"run_id": "run_status_detail", "status": "completed"}, log_path)
    operation_log_service.append_event("operation_failed", {"run_id": "other_run", "error": "other"}, log_path)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/query_ops_status.py",
            "--db",
            str(db),
            "--run-id",
            "run_status_detail",
            "--events",
            "5",
            "--log",
            str(log_path),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    status = json.loads(result.stdout)
    assert status["found"] is True
    assert status["run"]["approval_status"] == "approved"
    assert status["assets"][0]["asset_id"] == "asset_status_detail"
    assert status["reviews"][0]["reviewer_note"] == "Approved."
    assert [event["event_type"] for event in status["events"]] == ["operation_completed"]


def test_run_content_operation_plain_request_multi_image(tmp_path):
    db = tmp_path / "ops.sqlite3"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_content_operation.py",
            "--mode",
            "dry-run",
            "--request",
            "今日的爆品是牛肉恰巴塔，生成它的解构风展示图",
            "--image-count",
            "3",
            "--db",
            str(db),
            "--out-dir",
            str(tmp_path / "operations"),
            "--approval-out-dir",
            str(tmp_path / "approval_queue"),
            "--image-out-dir",
            str(tmp_path / "generated_images"),
            "--archive-out-dir",
            str(tmp_path / "operation_archive"),
            "--log",
            str(tmp_path / "operation_log.jsonl"),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    summary = json.loads(result.stdout)
    assert summary["content_task"]["product_name"] == "牛肉恰巴塔"
    assert summary["content_task"]["image_type"] == "deconstructed_exploded_view"
    assert summary["image_count"] == 3

    package_dir = Path(summary["approval_package"])
    metadata = json.loads((package_dir / "metadata.json").read_text(encoding="utf-8"))
    tasks = json.loads((package_dir / "tasks.json").read_text(encoding="utf-8"))
    image_prompt = json.loads((package_dir / "enhanced_image_prompt.json").read_text(encoding="utf-8"))
    assert metadata["content_task"]["natural_request"] == "今日的爆品是牛肉恰巴塔，生成它的解构风展示图"
    assert tasks
    assert len(image_prompt["variants"]) == 3
    assert metadata["assets"]["image_generation"]["asset_type"] == "image_batch"
    assert len(metadata["assets"]["image_generation"]["images"]) == 3


def test_run_content_operation_plain_request_detects_product_style_and_platform(tmp_path):
    db = tmp_path / "ops.sqlite3"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_content_operation.py",
            "--mode",
            "dry-run",
            "--request",
            "给开心果可颂做小红书切面特写",
            "--image-count",
            "2",
            "--db",
            str(db),
            "--out-dir",
            str(tmp_path / "operations"),
            "--approval-out-dir",
            str(tmp_path / "approval_queue"),
            "--image-out-dir",
            str(tmp_path / "generated_images"),
            "--archive-out-dir",
            str(tmp_path / "operation_archive"),
            "--log",
            str(tmp_path / "operation_log.jsonl"),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    summary = json.loads(result.stdout)
    assert summary["content_task"]["product_name"] == "开心果可颂"
    assert summary["content_task"]["image_type"] == "cutaway_detail"
    assert summary["content_task"]["platforms"] == "xiaohongshu"


def test_run_content_operation_rejects_unbounded_image_count(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_content_operation.py",
            "--mode",
            "dry-run",
            "--image-count",
            "20",
            "--db",
            str(tmp_path / "ops.sqlite3"),
            "--log",
            str(tmp_path / "operation_log.jsonl"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode != 0
    assert "--image-count must be between 1 and 8" in result.stderr


def test_validate_dify_outputs_rejects_missing_required_keys():
    from scripts import run_content_operation

    with pytest.raises(RuntimeError, match="missing required keys"):
        run_content_operation.validate_dify_outputs({"data": {"outputs": {"content_plan": {"theme": "x"}}}})


def test_run_content_operation_blocks_live_image_when_compliance_not_approved(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_content_operation.py",
            "--mode",
            "dry-run",
            "--live-image",
            "--db",
            str(tmp_path / "ops.sqlite3"),
            "--out-dir",
            str(tmp_path / "operations"),
            "--approval-out-dir",
            str(tmp_path / "approval_queue"),
            "--image-out-dir",
            str(tmp_path / "generated_images"),
            "--archive-out-dir",
            str(tmp_path / "operation_archive"),
            "--log",
            str(tmp_path / "operation_log.jsonl"),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    summary = json.loads(result.stdout)
    assert summary["live_image_requested"] is True
    assert summary["live_image_executed"] is False
    assert summary["live_image_blocked"] is True
    assert "compliance" in summary["live_image_block_reason"].lower()

    metadata = json.loads((Path(summary["approval_package"]) / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["live_image_blocked"] is True
    assert metadata["assets"]["image_generation"]["mode"] == "dry_run"
