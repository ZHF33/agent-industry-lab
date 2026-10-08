#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services import approval_service


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a human approval package from a Dify run.")
    parser.add_argument("--input", default="runs/bakery_latest_output.json")
    parser.add_argument("--image-prompt", default="runs/bakery_latest_image_prompt.json")
    parser.add_argument("--out-dir", default="runs/approval_queue")
    parser.add_argument("--campaign-id", default="")
    parser.add_argument("--product-name", default="bakery product")
    parser.add_argument("--platform", default="xiaohongshu,douyin")
    parser.add_argument("--content-goal", default="Generate review-ready bakery content")
    args = parser.parse_args()
    result = approval_service.create_approval_package(
        args.input,
        args.image_prompt,
        args.out_dir,
        campaign_id=args.campaign_id,
        product_name=args.product_name,
        platform=args.platform,
        content_goal=args.content_goal,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
