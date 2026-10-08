#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from services import dify_client

LEGACY_NOTICE = "LEGACY: prefer scripts/run_content_operation.py --mode live-dify for V2.0 operations."


def load_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def run_image_prompt_enhancer(input_path: str, out_json: str, out_md: str) -> None:
    subprocess.run(
        [
            sys.executable,
            "scripts/enhance_image_prompt.py",
            "--input",
            input_path,
            "--out-json",
            out_json,
            "--out-md",
            out_md,
        ],
        cwd=ROOT,
        check=True,
    )


def run_approval_packager(input_path: str, image_prompt_path: str) -> dict[str, Any]:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/create_approval_package.py",
            "--input",
            input_path,
            "--image-prompt",
            image_prompt_path,
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return json.loads(result.stdout)


def run_image_generator(image_prompt_path: str, live: bool, approval_package: str = "") -> dict[str, Any]:
    command = [
        sys.executable,
        "scripts/generate_openai_image.py",
        "--input",
        image_prompt_path,
    ]
    if approval_package:
        command.extend(["--approval-package", approval_package])
    if live:
        command.extend(["--live", "--require-key"])
    result = subprocess.run(
        command,
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return json.loads(result.stdout)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the local Dify workflow with generated knowledge context.")
    parser.add_argument("--product-query", default="daily bakery product")
    parser.add_argument(
        "--campaign-goal",
        default="Generate review-ready Xiaohongshu and Douyin bakery content with multiple image prompts. Video generation is skipped.",
    )
    parser.add_argument("--context", default="knowledge/processed/agent_context.md")
    parser.add_argument("--max-context-chars", type=int, default=4800)
    parser.add_argument("--out", default="runs/bakery_latest_output.json")
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--skip-image-prompt-enhance", action="store_true")
    parser.add_argument("--skip-approval-package", action="store_true")
    parser.add_argument("--skip-image-dry-run", action="store_true")
    parser.add_argument("--live-image", action="store_true", help="Call OpenAI Images API after prompt enhancement.")
    args = parser.parse_args()

    env = load_dotenv(ROOT / ".env")
    base_url = env.get("DIFY_BASE_URL") or os.environ.get("DIFY_BASE_URL", "")
    api_key = env.get("DIFY_API_KEY") or os.environ.get("DIFY_API_KEY", "")
    if not base_url or not api_key:
        raise RuntimeError("DIFY_BASE_URL and DIFY_API_KEY are required")

    context_path = ROOT / args.context
    product_knowledge = context_path.read_text(encoding="utf-8")
    if args.max_context_chars and len(product_knowledge) > args.max_context_chars:
        product_knowledge = (
            product_knowledge[: args.max_context_chars - 80].rstrip()
            + "\n\n## Context Truncated\nOutput was truncated for Dify input limits.\n"
        )

    payload = {
        "inputs": {
            "product_query": args.product_query,
            "campaign_goal": args.campaign_goal,
            "product_knowledge": product_knowledge,
            "brand_context": "Local bakery operation. Use only provided product facts; do not imply external brand authorization.",
            "platform_rules": "不自动发布；不夸大功效；不虚构价格、库存、产地、营养成分；不使用未经授权的Logo或产品图。",
            "date": date.today().isoformat(),
        },
        "response_mode": "blocking",
        "user": "local-bakery-python-test",
    }
    response = dify_client.call_workflow(base_url, api_key, payload, args.timeout)
    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(response, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    enhanced_prompt_file = ""
    if not args.skip_image_prompt_enhance:
        run_image_prompt_enhancer(
            args.out,
            "runs/bakery_latest_image_prompt.json",
            "runs/bakery_latest_image_prompt.md",
        )
        enhanced_prompt_file = "runs/bakery_latest_image_prompt.json"

    approval_package = {}
    if not args.skip_approval_package:
        approval_package = run_approval_packager(args.out, enhanced_prompt_file or "runs/bakery_latest_image_prompt.json")

    image_generation = {}
    if not args.skip_image_dry_run:
        image_generation = run_image_generator(
            enhanced_prompt_file or "runs/bakery_latest_image_prompt.json",
            args.live_image,
            approval_package.get("package_dir", ""),
        )

    data = response.get("data", {})
    outputs = data.get("outputs", {})
    summary = {
        "status": data.get("status"),
        "workflow_id": data.get("workflow_id"),
        "total_tokens": data.get("total_tokens"),
        "output_file": str(out_path.relative_to(ROOT)),
        "enhanced_image_prompt_file": enhanced_prompt_file,
        "image_generation": image_generation,
        "approval_package": approval_package.get("package_dir", ""),
        "output_keys": sorted(outputs.keys()),
        "legacy_notice": LEGACY_NOTICE,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
