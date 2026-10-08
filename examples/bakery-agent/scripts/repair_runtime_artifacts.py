#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.common import now_iso
from services.db_service import dumps


def parse_dt(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def resolve_existing_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def main() -> int:
    parser = argparse.ArgumentParser(description="Repair stale runtime DB task references.")
    parser.add_argument("--db", default="data/agent_ops.sqlite3")
    parser.add_argument("--max-pending-hours", type=int, default=24)
    parser.add_argument("--apply", action="store_true", help="Apply repairs. Default only reports planned changes.")
    args = parser.parse_args()

    db = ROOT / args.db if not Path(args.db).is_absolute() else Path(args.db)
    if not db.exists():
        raise RuntimeError(f"DB not found: {db}")

    cutoff = datetime.now() - timedelta(hours=args.max_pending_hours)
    repairs: list[dict[str, str]] = []

    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT task_id, status, related_package_path, output_json, error_message, created_at FROM tasks ORDER BY created_at"
        ).fetchall()
        for row in rows:
            created = parse_dt(row["created_at"])
            missing_package = bool(row["related_package_path"]) and not resolve_existing_path(row["related_package_path"]).exists()
            stale_pending = row["status"] == "pending" and created and created < cutoff
            if not (missing_package or stale_pending):
                continue

            action = {
                "task_id": row["task_id"],
                "from_status": row["status"],
                "to_status": "failed" if stale_pending else row["status"],
                "cleared_missing_package": str(missing_package).lower(),
            }
            repairs.append(action)
            if not args.apply:
                continue

            output = {}
            try:
                output = json.loads(row["output_json"] or "{}")
            except json.JSONDecodeError:
                output = {"previous_output": row["output_json"]}
            if not isinstance(output, dict):
                output = {"previous_output": output}
            output["runtime_repair"] = {
                "repaired_at": now_iso(),
                "reason": "stale_pending_task" if stale_pending else "missing_task_package",
                "previous_package_path": row["related_package_path"] if missing_package else "",
            }
            conn.execute(
                """
                UPDATE tasks
                SET status = ?, related_package_path = ?, output_json = ?, error_message = ?, updated_at = ?
                WHERE task_id = ?
                """,
                (
                    "failed" if stale_pending else row["status"],
                    "" if missing_package else row["related_package_path"],
                    dumps(output),
                    "Runtime repair marked stale task as failed." if stale_pending else row["error_message"],
                    now_iso(),
                    row["task_id"],
                ),
            )
        if args.apply:
            conn.commit()
    finally:
        conn.close()

    print(json.dumps({"db": str(db), "applied": args.apply, "repair_count": len(repairs), "repairs": repairs}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
