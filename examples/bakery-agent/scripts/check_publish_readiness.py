#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services import publisher_service

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check publish connector readiness.")
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--platforms", default="xiaohongshu,douyin")
    parser.add_argument("--require-live-ready", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    platforms = [item.strip() for item in args.platforms.split(",") if item.strip()]
    report = publisher_service.connector_readiness(args.env_file, platforms)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"Publish connector mode: {report['mode']}")
        print(f"Manual record ready: {report['manual_record_ready']}")
        print(f"Mock ready: {report['mock_ready']}")
        print(f"Live ready: {report['live_ready']}")
        for blocker in report["blockers"]:
            print(f"- {blocker}")
    return 1 if args.require_live_ready and not report["live_ready"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
