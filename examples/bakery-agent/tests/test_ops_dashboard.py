import json
import subprocess
import sys
from pathlib import Path

from services import db_service
from tests.test_update_approval_status import make_package


ROOT = Path(__file__).resolve().parents[1]


def test_ops_dashboard_json_includes_action_items(tmp_path):
    db = tmp_path / "ops.sqlite3"
    queue = tmp_path / "approval_queue"
    package = queue / "run_dashboard"
    make_package(package, status="needs_revision")

    with db_service.get_connection(db) as conn:
        db_service.upsert_content_run(
            conn,
            {
                "run_id": "run_dashboard",
                "product_name": "牛肉恰巴塔",
                "platform": "xiaohongshu",
                "approval_status": "needs_revision",
                "package_path": "/workspace/runs/approval_queue/run_dashboard",
                "created_at": "2026-07-01T00:00:00",
                "updated_at": "2026-07-01T00:01:00",
            },
        )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/ops_dashboard.py",
            "--db",
            str(db),
            "--queue",
            str(queue),
            "--json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )

    data = json.loads(result.stdout)
    assert data["queue_status_counts"]["needs_revision"] == 1
    assert data["action_item_count"] == 1
    assert data["action_items"][0]["product_name"] == "牛肉恰巴塔"
    assert data["next_actions"][0]["action"] == "create_revision"
    assert data["next_actions"][0]["suggested_payload"]["create_revision"] is True
    assert data["recent_runs"][0]["run_id"] == "run_dashboard"
    assert data["recent_runs"][0]["package_path"] == "runs/approval_queue/run_dashboard"


def test_ops_dashboard_text_output(tmp_path):
    db = tmp_path / "ops.sqlite3"
    queue = tmp_path / "approval_queue"
    make_package(queue / "run_dashboard", status="pending")
    result = subprocess.run(
        [sys.executable, "scripts/ops_dashboard.py", "--db", str(db), "--queue", str(queue)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    assert "Bakery AI Ops Dashboard" in result.stdout
    assert "Action items:" in result.stdout
    assert "Next actions:" in result.stdout


def test_ops_dashboard_next_action_mapping():
    from scripts import ops_dashboard

    pending = ops_dashboard.next_action_for({"status": "pending", "package_dir": "runs/approval_queue/run_1"})
    needs_revision = ops_dashboard.next_action_for({"status": "needs_revision", "package_dir": "runs/approval_queue/run_2"})
    pending_revision_review = ops_dashboard.next_action_for({"status": "pending_revision_review", "package_dir": "runs/approval_queue/run_3"})
    approved_needs_image = ops_dashboard.next_action_for(
        {"status": "approved", "image_status": "not_started", "package_dir": "runs/approval_queue/run_4"}
    )
    approved_prepared = ops_dashboard.next_action_for(
        {"status": "approved", "image_status": "prepared", "package_dir": "runs/approval_queue/run_6"}
    )
    approved_selected = ops_dashboard.next_action_for(
        {
            "status": "approved",
            "image_status": "completed",
            "image_has_files": True,
            "selected_image_has_file": True,
            "selected_image_id": "deconstructed",
            "publish_status": "",
            "package_dir": "runs/approval_queue/run_7",
        }
    )
    approved_done = ops_dashboard.next_action_for(
        {
            "status": "approved",
            "image_status": "completed",
            "image_has_files": True,
            "selected_image_has_file": True,
            "selected_image_id": "deconstructed",
            "publish_status": "published",
            "pending_publish_platforms": [],
            "package_dir": "runs/approval_queue/run_5",
        }
    )
    approved_draft_prepared = ops_dashboard.next_action_for(
        {
            "status": "approved",
            "image_status": "completed",
            "image_has_files": True,
            "selected_image_has_file": True,
            "selected_image_id": "deconstructed",
            "publish_status": "draft_prepared",
            "pending_publish_platforms": ["xiaohongshu", "douyin"],
            "package_dir": "runs/approval_queue/run_9",
        }
    )
    approved_partially_published = ops_dashboard.next_action_for(
        {
            "status": "approved",
            "image_status": "completed",
            "image_has_files": True,
            "selected_image_has_file": True,
            "selected_image_id": "deconstructed",
            "publish_status": "partially_published",
            "pending_publish_platforms": ["douyin"],
            "package_dir": "runs/approval_queue/run_10",
        }
    )
    approved_has_images_unselected = ops_dashboard.next_action_for(
        {
            "status": "approved",
            "image_status": "completed",
            "image_has_files": True,
            "image_ids": ["hero", "deconstructed"],
            "selected_image_id": "",
            "package_dir": "runs/approval_queue/run_8",
        }
    )

    assert pending["action"] == "human_review"
    assert needs_revision["action"] == "create_revision"
    assert needs_revision["suggested_payload"]["create_revision"] is True
    assert pending_revision_review["action"] == "review_revision"
    assert approved_needs_image["action"] == "generate_images"
    assert "/imagegenerationwebhook/" in approved_needs_image["webhook"].lower()
    assert approved_needs_image["suggested_payload"]["live"] is False
    assert approved_prepared["action"] == "generate_local_demo_images"
    assert approved_prepared["suggested_payload"]["local_demo"] is True
    assert approved_has_images_unselected["action"] == "select_image"
    assert approved_has_images_unselected["suggested_payload"]["image_id"] == "hero"
    assert "/imageselectionwebhook/" in approved_has_images_unselected["webhook"].lower()
    assert approved_selected["action"] == "prepare_publish_draft"
    assert "/publishdraftwebhook/" in approved_selected["webhook"].lower()
    assert approved_draft_prepared["action"] == "record_manual_publish"
    assert approved_draft_prepared["suggested_payload"]["platform"] == "xiaohongshu"
    assert "/publishrecordwebhook/" in approved_draft_prepared["webhook"].lower()
    assert approved_partially_published["action"] == "record_manual_publish"
    assert approved_partially_published["suggested_payload"]["platform"] == "douyin"
    assert approved_done["action"] == "none"


def test_ops_dashboard_includes_approved_image_generation_action(tmp_path):
    db = tmp_path / "ops.sqlite3"
    queue = tmp_path / "approval_queue"
    package = queue / "run_dashboard_image"
    make_package(package, status="approved")
    metadata = json.loads((package / "metadata.json").read_text(encoding="utf-8"))
    metadata["image_status"] = "not_started"
    (package / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/ops_dashboard.py",
            "--db",
            str(db),
            "--queue",
            str(queue),
            "--json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )

    data = json.loads(result.stdout)
    assert data["action_item_count"] == 1
    assert data["next_actions"][0]["action"] == "generate_images"
    assert data["next_actions"][0]["suggested_payload"]["package"].endswith("run_dashboard_image")
