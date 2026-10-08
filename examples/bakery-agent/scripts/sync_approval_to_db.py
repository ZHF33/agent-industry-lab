#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services import db_service, db_sync_service


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync approval package metadata into the local SQLite database.")
    parser.add_argument("--db", default=str(db_service.DEFAULT_DB.relative_to(db_service.ROOT)))
    parser.add_argument("--package", default="", help="Approval package directory. Defaults to all packages.")
    args = parser.parse_args()
    db_path = db_service.init_db(args.db)
    synced = 0
    with db_service.get_connection(db_path) as conn:
        for package in db_sync_service.load_packages(args.package):
            if db_sync_service.sync_package(conn, package):
                synced += 1
    print(json.dumps({"db": str(db_path), "synced_packages": synced}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
