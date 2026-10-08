#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services import db_service, image_generation_service, image_service
from services.common import ROOT, resolve_path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def resolve_package(args: argparse.Namespace) -> Path:
    if args.package:
        return resolve_path(args.package)
    if args.run_id:
        return image_generation_service.find_package_by_run_id(args.run_id, args.queue)
    return image_generation_service.latest_approved_package(args.queue)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate images for an approved Bakery AI approval package.")
    parser.add_argument("--package", default="", help="Approval package directory. Defaults to latest approved package.")
    parser.add_argument("--run-id", default="", help="Find approval package by run ID.")
    parser.add_argument("--queue", default="runs/approval_queue")
    parser.add_argument("--out-dir", default=image_service.DEFAULT_OUT_DIR)
    parser.add_argument("--db", default=str(db_service.DEFAULT_DB.relative_to(ROOT)))
    parser.add_argument("--live", action="store_true", help="Actually call OpenAI Images API. Default is dry-run metadata.")
    parser.add_argument("--local-demo", action="store_true", help="Generate local demo PNG images without calling a paid provider.")
    parser.add_argument("--require-key", action="store_true", help="Fail if OPENAI_API_KEY is missing.")
    parser.add_argument("--allow-unapproved", action="store_true", help="Allow testing against non-approved packages.")
    parser.add_argument("--n", type=int, default=1)
    args = parser.parse_args()

    result = image_generation_service.generate_for_package(
        resolve_package(args),
        out_dir=args.out_dir,
        live=args.live,
        require_key=args.require_key,
        n=args.n,
        db=args.db,
        local_demo=args.local_demo,
        allow_unapproved=args.allow_unapproved,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
