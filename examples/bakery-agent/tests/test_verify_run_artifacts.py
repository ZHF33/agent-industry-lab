import json
import sqlite3
import subprocess
import sys
from pathlib import Path

from scripts import verify_run_artifacts
from services import db_service


ROOT = Path(__file__).resolve().parents[1]


def make_verified_run(tmp_path: Path):
    package = tmp_path / "approval_queue" / "run_verified"
    image = tmp_path / "generated_images" / "selected.png"
    db = tmp_path / "ops.sqlite3"
    package.mkdir(parents=True)
    image.parent.mkdir(parents=True)
    image.write_bytes(b"png")
    metadata = {
        "run_id": "run_verified",
        "campaign_id": "campaign_verified",
        "product_name": "Beef ciabatta",
        "platform": "xiaohongshu,douyin",
        "approval_status": "approved",
        "image_status": "completed",
        "selected_image_id": "deconstructed",
        "publish_status": "published",
        "publish_records": [{"platform": "xiaohongshu"}, {"platform": "douyin"}],
        "assets": {
            "image_generation": {
                "selected_image_id": "deconstructed",
                "selected_image": {"image_id": "deconstructed", "image_paths": [str(image)]},
            }
        },
    }
    (package / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")
    for name in ["review.md", "publish_draft.md", "product_flow.md"]:
        (package / name).write_text("ok", encoding="utf-8")
    for name in ["enhanced_image_prompt.json", "publish_draft.json", "publish_record.json"]:
        (package / name).write_text("{}", encoding="utf-8")
    with db_service.get_connection(db) as conn:
        db_service.upsert_campaign(conn, {"campaign_id": "campaign_verified", "campaign_name": "Verified campaign", "status": "active"})
        db_service.upsert_content_run(conn, {"run_id": "run_verified", "campaign_id": "campaign_verified", "approval_status": "approved", "package_path": str(package)})
        db_service.upsert_task(conn, {"task_id": "task_publish", "task_type": "manual_publish_record", "status": "succeeded", "related_run_id": "run_verified"})
        for platform in ["xiaohongshu", "douyin"]:
            db_service.upsert_campaign_history(conn, {"history_id": f"run_verified_{platform}", "campaign_id": "campaign_verified", "run_id": "run_verified", "platform": platform})
    return package, db


def test_verify_run_artifacts_accepts_complete_run(tmp_path):
    package, db = make_verified_run(tmp_path)

    result = verify_run_artifacts.verify(package=str(package), db=db)

    assert result["ok"] is True
    assert result["issues"] == []
    assert result["evidence"]["selected_image_id"] == "deconstructed"


def test_verify_run_artifacts_reports_missing_publish_history(tmp_path):
    package, db = make_verified_run(tmp_path)
    with sqlite3.connect(db) as conn:
        conn.execute("DELETE FROM campaign_history WHERE platform = ?", ("douyin",))

    result = verify_run_artifacts.verify(package=str(package), db=db)

    assert result["ok"] is False
    assert {"type": "missing_db_campaign_history", "platform": "douyin"} in result["issues"]


def test_verify_run_artifacts_cli_json(tmp_path):
    package, db = make_verified_run(tmp_path)
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/verify_run_artifacts.py",
            "--package",
            str(package),
            "--db",
            str(db),
            "--json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )

    data = json.loads(completed.stdout)
    assert data["ok"] is True
