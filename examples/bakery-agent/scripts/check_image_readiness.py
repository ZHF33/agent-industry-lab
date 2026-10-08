#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services import image_service

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check OpenAI image generation readiness.")
    parser.add_argument("--require-agent-api-allow", action="store_true", help="Also require AGENT_API_ALLOW_LIVE_IMAGE=true.")
    parser.add_argument("--require-ready", action="store_true", help="Exit non-zero when live image generation is not ready.")
    args = parser.parse_args()

    report = image_service.live_image_readiness(require_agent_api_allow=args.require_agent_api_allow)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if args.require_ready and not report["ready"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
