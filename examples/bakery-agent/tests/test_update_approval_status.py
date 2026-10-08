import json
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def make_package(package_dir: Path, status: str = "pending") -> None:
    package_dir.mkdir(parents=True)
    (package_dir / "metadata.json").write_text(
        json.dumps(
            {
                "run_id": package_dir.name,
                "status": status,
                "approval_status": status,
                "product_name": "牛肉恰巴塔",
                "platform": "xiaohongshu,douyin",
                "content_goal": "demo",
                "content_task": {"content_type": "best_seller_feature", "image_type": "deconstructed"},
                "created_at": "2026-07-01T00:00:00",
                "updated_at": "2026-07-01T00:00:00",
                "assets": {"image_generation": {"images": [{"image_id": "hero"}]}},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (package_dir / "review.md").write_text("# Approval Package\n\n## Manual Notes\n\n- ", encoding="utf-8")
    (package_dir / "tasks.json").write_text("[]", encoding="utf-8")
    (package_dir / "assets.json").write_text("[]", encoding="utf-8")
    (package_dir / "enhanced_image_prompt.json").write_text("{}", encoding="utf-8")


def test_update_approval_status_records_note_and_syncs_db(tmp_path):
    db_path = tmp_path / "agent_ops.sqlite3"
    package_dir = tmp_path / "approval_queue" / "run_test"
    make_package(package_dir)

    subprocess.run(
        [
            sys.executable,
            "scripts/update_approval_status.py",
            "--package",
            str(package_dir),
            "--status",
            "needs_revision",
            "--note",
            "删除官方包装镜头，重写 CTA。",
            "--db",
            str(db_path),
        ],
        cwd=ROOT,
        check=True,
    )

    metadata = json.loads((package_dir / "metadata.json").read_text(encoding="utf-8"))
    review = (package_dir / "review.md").read_text(encoding="utf-8")
    assert metadata["status"] == "needs_revision"
    assert metadata["review_notes"][0]["note"] == "删除官方包装镜头，重写 CTA。"
    assert "status=needs_revision" in review
    assert "删除官方包装镜头" in review
    with sqlite3.connect(db_path) as conn:
        status = conn.execute("SELECT approval_status FROM content_runs WHERE run_id = ?", ("run_test",)).fetchone()[0]
        note = conn.execute("SELECT reviewer_note FROM approval_reviews WHERE run_id = ?", ("run_test",)).fetchone()[0]
    assert status == "needs_revision"
    assert "官方包装" in note

    subprocess.run(
        [
            sys.executable,
            "scripts/sync_approval_to_db.py",
            "--package",
            str(package_dir),
            "--db",
            str(db_path),
        ],
        cwd=ROOT,
        check=True,
    )
    with sqlite3.connect(db_path) as conn:
        review_count = conn.execute("SELECT COUNT(*) FROM approval_reviews WHERE run_id = ?", ("run_test",)).fetchone()[0]
    assert review_count == 1


def test_list_approval_queue_filters_pending(tmp_path):
    queue = tmp_path / "approval_queue"
    package_dir = queue / "run_20260701_000000"
    make_package(package_dir)
    result = subprocess.run(
        [
            sys.executable,
            "scripts/list_approval_queue.py",
            "--queue",
            str(queue),
            "--status",
            "pending",
            "--json",
        ],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=True,
    )
    data = json.loads(result.stdout)
    assert data["count"] == 1
    assert data["packages"][0]["product_name"] == "牛肉恰巴塔"
    assert data["packages"][0]["image_count"] == 1
