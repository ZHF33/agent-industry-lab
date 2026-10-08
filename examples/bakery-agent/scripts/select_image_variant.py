#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services import db_service, image_generation_service, image_selection_service
from services.common import ROOT, resolve_path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def resolve_package(args: argparse.Namespace) -> Path:
    if args.package:
        return resolve_path(args.package)
    if args.run_id:
        return image_generation_service.find_package_by_run_id(args.run_id, args.queue)
    raise RuntimeError("--package or --run-id is required")


def main() -> int:
    parser = argparse.ArgumentParser(description="Select one prepared/generated image variant for an approval package.")
    parser.add_argument("--package", default="", help="Approval package directory.")
    parser.add_argument("--run-id", default="", help="Find approval package by run ID.")
    parser.add_argument("--queue", default="runs/approval_queue")
    parser.add_argument("--image-id", required=True, help="Variant/image ID to select, for example cutaway_detail or hero.")
    parser.add_argument("--note", default="")
    parser.add_argument("--db", default=str(db_service.DEFAULT_DB.relative_to(ROOT)))
    parser.add_argument("--no-sync-db", action="store_true")
    args = parser.parse_args()

    result = image_selection_service.select_image_variant(
        str(resolve_package(args)),
        args.image_id,
        note=args.note,
        db=args.db,
        sync_db=not args.no_sync_db,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
