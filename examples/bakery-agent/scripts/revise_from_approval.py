#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services import db_service, db_sync_service, revision_service
from services.common import ROOT, write_json


def find_latest_approval_package() -> Path:
    queue = ROOT / "runs" / "approval_queue"
    packages = [path for path in queue.glob("run_*") if path.is_dir()]
    if not packages:
        raise RuntimeError("No approval package found under runs/approval_queue")
    return max(packages, key=lambda path: path.stat().st_mtime)


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare or run a Dify revision from an approval package.")
    parser.add_argument("--package", default="", help="Approval package directory. Defaults to latest package.")
    parser.add_argument("--note", default="", help="Additional revision instruction.")
    parser.add_argument("--out-dir", default="runs/revisions")
    parser.add_argument("--db", default=str(db_service.DEFAULT_DB.relative_to(ROOT)))
    parser.add_argument("--no-sync-db", action="store_true", help="Do not sync the package status into SQLite after preparing revision.")
    parser.add_argument("--live", action="store_true", help="Call Dify with the revision payload.")
    parser.add_argument("--timeout", type=int, default=240)
    args = parser.parse_args()

    package_dir = args.package or str(find_latest_approval_package())
    prepared = revision_service.create_revision_request(package_dir, note=args.note, out_dir=args.out_dir)
    response = revision_service.call_dify_revision_workflow(prepared["payload"], dry_run=not args.live, timeout=args.timeout)
    output_path = ""
    if args.live:
        out = Path(prepared["revision_request"]).with_name(Path(prepared["revision_request"]).name.replace("_request_", "_output_"))
        write_json(out, response)
        output_path = str(out)
    db_sync_status = "skipped"
    if not args.no_sync_db:
        with db_service.get_connection(args.db) as conn:
            db_sync_status = "synced" if db_sync_service.sync_package(conn, Path(prepared["package_dir"])) else "skipped"
    print(
        json.dumps(
            {
                "mode": "live" if args.live else "dry_run",
                "package_dir": package_dir,
                "revision_request": prepared["revision_request"],
                "revision_output": output_path,
                "approval_status": "pending_revision_review",
                "db_sync_status": db_sync_status,
                "db": str(Path(args.db)),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
