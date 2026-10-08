#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services import db_service, operation_log_service
from services.common import resolve_path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def fetch_all(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    return [dict(row) for row in conn.execute(sql, params).fetchall()]


def fetch_one(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any]:
    row = conn.execute(sql, params).fetchone()
    return dict(row) if row else {}


def event_matches_run(event: dict[str, Any], run_id: str) -> bool:
    if not run_id:
        return True
    payload = event.get("payload", {})
    return run_id in json.dumps(payload, ensure_ascii=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Query local V2.0 operation status.")
    parser.add_argument("--db", default=str(db_service.DEFAULT_DB.relative_to(db_service.ROOT)))
    parser.add_argument("--latest", action="store_true")
    parser.add_argument("--run-id", default="", help="Query one content run with assets, reviews, and tasks.")
    parser.add_argument("--pending-approval", action="store_true")
    parser.add_argument("--campaign", default="")
    parser.add_argument("--events", type=int, default=0)
    parser.add_argument("--log", default=str(operation_log_service.DEFAULT_LOG.relative_to(db_service.ROOT)))
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    db_path = db_service.init_db(args.db)
    result: dict[str, Any] = {"db": str(resolve_path(db_path))}
    with db_service.get_connection(db_path) as conn:
        if args.run_id:
            result["run"] = fetch_one(conn, "SELECT * FROM content_runs WHERE run_id = ?", (args.run_id,))
            result["assets"] = fetch_all(conn, "SELECT * FROM generated_assets WHERE run_id = ? ORDER BY updated_at DESC", (args.run_id,))
            result["reviews"] = fetch_all(conn, "SELECT * FROM approval_reviews WHERE run_id = ? ORDER BY updated_at DESC", (args.run_id,))
            result["tasks"] = fetch_all(conn, "SELECT * FROM tasks WHERE related_run_id = ? ORDER BY updated_at DESC", (args.run_id,))
            result["found"] = bool(result["run"])
        elif args.pending_approval:
            result["pending_approval"] = fetch_all(
                conn,
                "SELECT * FROM content_runs WHERE approval_status = 'pending' ORDER BY updated_at DESC LIMIT ?",
                (args.limit,),
            )
        elif args.campaign:
            result["campaign"] = fetch_all(conn, "SELECT * FROM campaigns WHERE campaign_id = ?", (args.campaign,))
            result["runs"] = fetch_all(
                conn,
                "SELECT * FROM content_runs WHERE campaign_id = ? ORDER BY updated_at DESC LIMIT ?",
                (args.campaign, args.limit),
            )
        else:
            result["latest_runs"] = db_service.query_recent_runs(conn, args.limit)

    if args.events:
        event_limit = args.events
        if args.run_id:
            recent = operation_log_service.load_recent_events(max(args.events * 20, args.events), args.log)
            result["events"] = [event for event in recent if event_matches_run(event, args.run_id)][-event_limit:]
        else:
            result["events"] = operation_log_service.load_recent_events(event_limit, args.log)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
