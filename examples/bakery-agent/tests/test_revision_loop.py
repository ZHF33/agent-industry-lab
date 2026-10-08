import json
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_revise_from_approval_dry_run(tmp_path):
    source_output = tmp_path / "source_output.json"
    source_output.write_text(
        json.dumps({"data": {"outputs": {"douyin_script": "{\"visual\":\"展示官方包装\"}"}}}, ensure_ascii=False),
        encoding="utf-8",
    )
    package_dir = tmp_path / "approval_queue" / "chagee_test"
    package_dir.mkdir(parents=True)
    (package_dir / "metadata.json").write_text(
        json.dumps(
            {
                "package_id": "chagee_test",
                "status": "needs_revision",
                "source_output": str(source_output),
                "review_notes": [
                    {
                        "created_at": "2026-06-19T00:00:00",
                        "status": "needs_revision",
                        "note": "删除官方包装镜头。",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (package_dir / "review.md").write_text("# Approval Package\n\n## Reviewer Notes\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/revise_from_approval.py",
            "--package",
            str(package_dir),
            "--out-dir",
            str(tmp_path / "revisions"),
            "--db",
            str(tmp_path / "ops.sqlite3"),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    report = json.loads(result.stdout)
    request_path = Path(report["revision_request"])
    payload = json.loads(request_path.read_text(encoding="utf-8"))
    assert report["mode"] == "dry_run"
    assert report["approval_status"] == "pending_revision_review"
    assert report["db_sync_status"] == "synced"
    assert "删除官方包装镜头" in payload["inputs"]["product_knowledge"]
    metadata = json.loads((package_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["revisions"][0]["status"] == "prepared"
    assert metadata["approval_status"] == "pending_revision_review"
    with sqlite3.connect(tmp_path / "ops.sqlite3") as conn:
        status = conn.execute("SELECT approval_status FROM content_runs WHERE run_id = ?", ("chagee_test",)).fetchone()[0]
    assert status == "pending_revision_review"
