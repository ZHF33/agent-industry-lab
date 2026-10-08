#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def parse_dt(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def exists_path(value: str) -> bool:
    if not value:
        return True
    if value.startswith("/workspace/"):
        return (ROOT / value.removeprefix("/workspace/")).exists()
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path.exists()


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit runtime DB and artifact consistency.")
    parser.add_argument("--db", default="data/agent_ops.sqlite3")
    parser.add_argument("--max-pending-hours", type=int, default=24)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    db = ROOT / args.db if not Path(args.db).is_absolute() else Path(args.db)
    issues: list[dict[str, str]] = []
    if not db.exists():
        issues.append({"severity": "error", "type": "missing_db", "message": f"DB not found: {db}"})
    else:
        cutoff = datetime.now() - timedelta(hours=args.max_pending_hours)
        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row
        for row in conn.execute("SELECT task_id, status, related_package_path, created_at FROM tasks ORDER BY created_at"):
            created = parse_dt(row["created_at"])
            if row["status"] == "pending" and created and created < cutoff:
                issues.append({"severity": "error", "type": "stale_pending_task", "task_id": row["task_id"], "created_at": row["created_at"]})
            if row["related_package_path"] and not exists_path(row["related_package_path"]):
                issues.append({"severity": "error", "type": "missing_task_package", "task_id": row["task_id"], "path": row["related_package_path"]})
        for row in conn.execute("SELECT run_id, package_path FROM content_runs ORDER BY created_at"):
            if row["package_path"] and not exists_path(row["package_path"]):
                issues.append({"severity": "error", "type": "missing_content_run_package", "run_id": row["run_id"], "path": row["package_path"]})

    result = {"db": str(db), "issue_count": len(issues), "issues": issues}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if issues:
            print("Runtime audit failed:")
            for issue in issues:
                detail = ", ".join(f"{k}={v}" for k, v in issue.items())
                print(f"- {detail}")
        else:
            print("Runtime audit passed.")
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
