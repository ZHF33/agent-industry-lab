import json
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_init_and_sync_local_db(tmp_path):
    db_path = tmp_path / "agent_ops.sqlite3"
    package_dir = tmp_path / "approval_queue" / "chagee_test"
    package_dir.mkdir(parents=True)
    (package_dir / "metadata.json").write_text(
        json.dumps(
            {
                "run_id": "run_test",
                "agent_name": "霸王茶姬 AI Operation Agent V1",
                "approval_status": "needs_revision",
                "product_name": "伯牙绝弦",
                "platform": "xiaohongshu",
                "source_output": "runs/chagee_latest_output.json",
                "source_image_prompt": "runs/chagee_latest_image_prompt.json",
                "created_at": "2026-06-19T00:00:00",
                "updated_at": "2026-06-19T00:01:00",
                "assets": {
                    "image_generation": {
                        "status": "prepared",
                        "provider": "openai",
                        "model": "gpt-image-2",
                        "metadata_path": "runs/generated_images/test.json",
                        "image_paths": [],
                        "review_status": "pending",
                    }
                },
                "review_notes": [
                    {
                        "created_at": "2026-06-19T00:01:00",
                        "status": "needs_revision",
                        "note": "删除官方包装镜头。",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    subprocess.run([sys.executable, "scripts/init_local_db.py", "--db", str(db_path)], cwd=ROOT, check=True)
    subprocess.run(
        [sys.executable, "scripts/sync_approval_to_db.py", "--db", str(db_path), "--package", str(package_dir)],
        cwd=ROOT,
        check=True,
    )

    with sqlite3.connect(db_path) as conn:
        status = conn.execute("SELECT approval_status FROM content_runs WHERE run_id = ?", ("run_test",)).fetchone()[0]
        asset = conn.execute("SELECT provider FROM generated_assets WHERE run_id = ?", ("run_test",)).fetchone()[0]
        note = conn.execute("SELECT reviewer_note FROM approval_reviews WHERE run_id = ?", ("run_test",)).fetchone()[0]
    assert status == "needs_revision"
    assert asset == "openai"
    assert "官方包装" in note
