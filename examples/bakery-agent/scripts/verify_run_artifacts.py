#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.common import read_json, resolve_path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

IMAGE_COMPLETE_STATUSES = {"completed", "generated", "prepared"}


def _platforms(value: str) -> list[str]:
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def _path_exists(value: str) -> bool:
    if not value:
        return False
    return resolve_path(value).exists()


def _package_from_args(run_id: str, package: str) -> Path:
    if package:
        return resolve_path(package)
    if not run_id:
        raise ValueError("Either --run-id or --package is required.")
    return resolve_path(Path("runs") / "approval_queue" / run_id)


def _db_rows(db: str | Path, run_id: str) -> dict[str, Any]:
    db_path = resolve_path(db)
    if not db_path.exists():
        return {"db_exists": False, "db": str(db_path), "content_run": None, "history": [], "tasks": [], "assets": []}
    with sqlite3.connect(str(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        content_run = conn.execute("SELECT run_id, approval_status, package_path FROM content_runs WHERE run_id = ?", (run_id,)).fetchone()
        history = conn.execute("SELECT platform, published_at FROM campaign_history WHERE run_id = ? ORDER BY platform", (run_id,)).fetchall()
        tasks = conn.execute("SELECT task_type, status FROM tasks WHERE related_run_id = ? ORDER BY task_type", (run_id,)).fetchall()
        assets = conn.execute("SELECT asset_type, status, local_path FROM generated_assets WHERE run_id = ? ORDER BY asset_type, local_path", (run_id,)).fetchall()
    return {
        "db_exists": True,
        "db": str(db_path),
        "content_run": dict(content_run) if content_run else None,
        "history": [dict(row) for row in history],
        "tasks": [dict(row) for row in tasks],
        "assets": [dict(row) for row in assets],
    }


def verify(run_id: str = "", package: str = "", db: str | Path = "data/agent_ops.sqlite3") -> dict[str, Any]:
    package_dir = _package_from_args(run_id, package)
    issues: list[dict[str, Any]] = []
    evidence: dict[str, Any] = {"package_dir": str(package_dir)}

    if not package_dir.exists():
        return {"ok": False, "run_id": run_id or package_dir.name, "issues": [{"type": "missing_package", "path": str(package_dir)}], "evidence": evidence}

    metadata = read_json(package_dir / "metadata.json", {})
    actual_run_id = str(metadata.get("run_id") or run_id or package_dir.name)
    evidence["run_id"] = actual_run_id
    evidence["product_name"] = metadata.get("product_name", "")
    evidence["approval_status"] = metadata.get("approval_status", metadata.get("status", ""))
    evidence["image_status"] = metadata.get("image_status", "")
    evidence["selected_image_id"] = metadata.get("selected_image_id") or metadata.get("assets", {}).get("image_generation", {}).get("selected_image_id", "")
    evidence["publish_status"] = metadata.get("publish_status", "")

    if not metadata:
        issues.append({"type": "missing_metadata", "path": str(package_dir / "metadata.json")})
    if evidence["approval_status"] != "approved":
        issues.append({"type": "approval_not_approved", "status": evidence["approval_status"]})
    if evidence["image_status"] not in IMAGE_COMPLETE_STATUSES:
        issues.append({"type": "image_not_complete", "status": evidence["image_status"]})
    if not evidence["selected_image_id"]:
        issues.append({"type": "missing_selected_image_id"})

    selected = metadata.get("assets", {}).get("image_generation", {}).get("selected_image", {}) if isinstance(metadata.get("assets"), dict) else {}
    selected_paths = selected.get("image_paths", []) if isinstance(selected, dict) else []
    existing_selected_paths = [path for path in selected_paths if _path_exists(path)]
    evidence["selected_image_paths"] = selected_paths
    evidence["existing_selected_image_paths"] = existing_selected_paths
    if not existing_selected_paths:
        issues.append({"type": "missing_selected_image_file", "paths": selected_paths})

    for filename in ["review.md", "enhanced_image_prompt.json", "publish_draft.json", "publish_draft.md", "publish_record.json", "product_flow.md"]:
        exists = (package_dir / filename).exists()
        evidence[f"{filename}_exists"] = exists
        if not exists:
            issues.append({"type": "missing_package_file", "file": filename})

    platforms = _platforms(metadata.get("platform", ""))
    records = metadata.get("publish_records", [])
    record_platforms = [str(record.get("platform", "")) for record in records if isinstance(record, dict)]
    evidence["platforms"] = platforms
    evidence["publish_record_platforms"] = record_platforms
    if metadata.get("publish_status") != "published":
        issues.append({"type": "publish_not_complete", "status": metadata.get("publish_status", "")})
    for platform in platforms:
        if platform not in record_platforms:
            issues.append({"type": "missing_publish_record", "platform": platform})

    db_evidence = _db_rows(db, actual_run_id)
    evidence["db"] = db_evidence
    if not db_evidence["db_exists"]:
        issues.append({"type": "missing_db", "path": db_evidence["db"]})
    else:
        if not db_evidence["content_run"]:
            issues.append({"type": "missing_db_content_run", "run_id": actual_run_id})
        db_history_platforms = [row["platform"] for row in db_evidence["history"]]
        for platform in platforms:
            if platform not in db_history_platforms:
                issues.append({"type": "missing_db_campaign_history", "platform": platform})
        if not any(task["task_type"] == "manual_publish_record" and task["status"] == "succeeded" for task in db_evidence["tasks"]):
            issues.append({"type": "missing_db_manual_publish_task"})

    return {"ok": not issues, "run_id": actual_run_id, "issues": issues, "evidence": evidence}


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a completed Bakery AI Agent run has required files and SQLite records.")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--package", default="")
    parser.add_argument("--db", default="data/agent_ops.sqlite3")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = verify(args.run_id, args.package, args.db)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"ok: {result['ok']}")
        print(f"run_id: {result['run_id']}")
        for issue in result["issues"]:
            print(f"issue: {json.dumps(issue, ensure_ascii=False)}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
