import json
import subprocess
import sys
from pathlib import Path

from services import db_service
from tests.test_update_approval_status import make_package


ROOT = Path(__file__).resolve().parents[1]


def seed_run(db: Path, run_id: str, package: Path, status: str = "needs_revision") -> None:
    with db_service.get_connection(db) as conn:
        db_service.upsert_content_run(
            conn,
            {
                "run_id": run_id,
                "product_name": "牛肉恰巴塔",
                "platform": "xiaohongshu",
                "approval_status": status,
                "package_path": str(package),
                "created_at": "2026-07-01T00:00:00",
                "updated_at": "2026-07-01T00:01:00",
            },
        )


def test_apply_next_action_dry_run_uses_dashboard_payload(tmp_path):
    db = tmp_path / "ops.sqlite3"
    queue = tmp_path / "approval_queue"
    package = queue / "run_apply_action"
    make_package(package, status="needs_revision")
    seed_run(db, "run_apply_action", package)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/apply_next_action.py",
            "--db",
            str(db),
            "--queue",
            str(queue),
            "--run-id",
            "run_apply_action",
            "--json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )

    data = json.loads(result.stdout)
    assert data["ok"] is True
    assert data["mode"] == "dry_run"
    assert data["action"]["action"] == "create_revision"
    assert data["action"]["product_name"] == "牛肉恰巴塔"
    assert data["payload"]["status"] == "needs_revision"
    assert data["payload"]["create_revision"] is True
    assert data["payload"]["package"].endswith("run_apply_action")
    assert "webhook_secret" not in data["payload"]


def test_apply_next_action_allows_manual_overrides(tmp_path):
    db = tmp_path / "ops.sqlite3"
    queue = tmp_path / "approval_queue"
    package = queue / "run_apply_override"
    make_package(package, status="pending_revision_review")
    seed_run(db, "run_apply_override", package, status="pending_revision_review")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/apply_next_action.py",
            "--db",
            str(db),
            "--queue",
            str(queue),
            "--package",
            str(package),
            "--status",
            "approved",
            "--note",
            "图片结构清楚，标题可发布。",
            "--no-create-revision",
            "--json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )

    data = json.loads(result.stdout)
    assert data["mode"] == "dry_run"
    assert data["action"]["action"] == "review_revision"
    assert data["payload"]["status"] == "approved"
    assert data["payload"]["note"] == "图片结构清楚，标题可发布。"
    assert data["payload"]["create_revision"] is False


def test_apply_next_action_uses_image_webhook_for_approved_image_action(tmp_path):
    db = tmp_path / "ops.sqlite3"
    queue = tmp_path / "approval_queue"
    package = queue / "run_apply_image"
    make_package(package, status="approved")
    metadata = json.loads((package / "metadata.json").read_text(encoding="utf-8"))
    metadata["image_status"] = "not_started"
    (package / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")
    seed_run(db, "run_apply_image", package, status="approved")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/apply_next_action.py",
            "--db",
            str(db),
            "--queue",
            str(queue),
            "--run-id",
            "run_apply_image",
            "--json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )

    data = json.loads(result.stdout)
    assert data["action"]["action"] == "generate_images"
    assert "/imagegenerationwebhook/" in data["webhook"].lower()
    assert data["payload"]["live"] is False
    assert data["payload"]["out_dir"] == "runs/generated_images"


def test_apply_next_action_execute_requires_webhook_secret(tmp_path):
    db = tmp_path / "ops.sqlite3"
    queue = tmp_path / "approval_queue"
    package = queue / "run_apply_execute_secret"
    make_package(package, status="pending")
    seed_run(db, "run_apply_execute_secret", package, status="pending")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/apply_next_action.py",
            "--db",
            str(db),
            "--queue",
            str(queue),
            "--run-id",
            "run_apply_execute_secret",
            "--execute",
            "--webhook-url",
            "http://127.0.0.1:1/not-called",
            "--env-file",
            str(tmp_path / "missing.env"),
            "--json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode != 0
    assert "N8N_WEBHOOK_SECRET is required" in result.stderr
