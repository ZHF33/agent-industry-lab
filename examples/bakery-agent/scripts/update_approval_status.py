#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services import approval_service, db_service, db_sync_service
from services.common import ROOT


def find_latest_approval_package() -> Path:
    queue = ROOT / "runs" / "approval_queue"
    packages = [path for path in queue.glob("run_*") if path.is_dir()]
    if not packages:
        raise RuntimeError("No approval package found under runs/approval_queue")
    return max(packages, key=lambda path: path.stat().st_mtime)


def main() -> int:
    parser = argparse.ArgumentParser(description="Update approval package status and reviewer notes.")
    parser.add_argument("--package", default="", help="Approval package directory. Defaults to latest package.")
    parser.add_argument("--status", required=True, choices=sorted(approval_service.ALLOWED_STATUSES))
    parser.add_argument("--note", default="")
    parser.add_argument("--db", default=str(db_service.DEFAULT_DB.relative_to(ROOT)))
    parser.add_argument("--no-sync-db", action="store_true", help="Only update files; do not sync SQLite.")
    args = parser.parse_args()
    package_dir = args.package or str(find_latest_approval_package())
    result = approval_service.update_approval_status(package_dir, args.status, args.note)
    if not args.no_sync_db:
        with db_service.get_connection(args.db) as conn:
            db_sync_service.sync_package(conn, Path(package_dir))
        result["db_sync_status"] = "synced"
        result["db"] = str((ROOT / args.db).resolve() if not Path(args.db).is_absolute() else Path(args.db))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
