#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services import approval_service, campaign_service, content_request_service, db_service, db_sync_service, dify_client, image_prompt_service, image_service, knowledge_service, operation_log_service, task_service
from services.common import ROOT, load_dotenv, now_iso, parse_json_text, resolve_path, write_json

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SELECTED_LOG = str(operation_log_service.DEFAULT_LOG.relative_to(ROOT))
ACTIVE_DB = str(db_service.DEFAULT_DB.relative_to(ROOT))
ACTIVE_TASK_IDS: list[str] = []
MAX_IMAGE_COUNT = 8
REQUIRED_DIFY_OUTPUT_KEYS = {"content_plan", "xiaohongshu_copy", "douyin_script", "image_prompt", "compliance_result"}


def build_content_task(args: argparse.Namespace) -> dict[str, Any]:
    if args.request:
        return content_request_service.parse_natural_request(
            args.request,
            {
                key: value
                for key, value in {
                    "product_name": None if args.product_query == "daily_bakery_product" else args.product_query,
                    "content_type": None if args.content_type == "daily_product_content" else args.content_type,
                    "image_type": None if args.image_type == "product_hero" else args.image_type,
                    "image_style": None if args.image_style == "realistic bakery product photography" else args.image_style,
                    "platforms": None if args.platform == "xiaohongshu,douyin" else args.platform,
                    "campaign_goal": None
                    if args.campaign_goal == "Generate review-ready Xiaohongshu and Douyin content with multiple image prompts. Video generation is skipped."
                    else args.campaign_goal,
                    "audience": None if args.audience == "local bakery customers" else args.audience,
                    "constraints": args.constraints,
                }.items()
                if value
            },
        )
    return {
        "natural_request": "",
        "product_name": args.product_query,
        "content_type": args.content_type,
        "image_type": args.image_type,
        "image_style": args.image_style,
        "visual_intent": "",
        "platforms": args.platform,
        "campaign_goal": args.campaign_goal,
        "audience": args.audience,
        "constraints": args.constraints,
    }


def dry_run_dify_outputs(task: dict[str, Any]) -> dict[str, Any]:
    product_name = task["product_name"]
    return {
        "data": {
            "status": "dry_run",
            "workflow_id": "local-v2-dry-run",
            "total_tokens": 0,
            "outputs": {
                "content_plan": {
                    "theme": "Dynamic bakery content task",
                    "product_name": product_name,
                    "content_type": task["content_type"],
                    "image_type": task["image_type"],
                    "image_style": task["image_style"],
                    "visual_intent": task.get("visual_intent", ""),
                    "campaign_goal": task["campaign_goal"],
                },
                "xiaohongshu_copy": {
                    "title": f"{product_name} content draft",
                    "cover_text": product_name,
                    "body": "Local dry-run draft for review. Edit product facts before publishing.",
                    "cta": "Save for manual review.",
                },
                "douyin_script": {
                    "hook": f"Open with a close-up of {product_name}.",
                    "shots": ["product close-up", "bakery counter scene", "packaging or plating handoff"],
                    "cta": "Send to manual review before publishing.",
                },
                "image_prompt": {
                    "aspect_ratio": "1:1",
                    "prompt_en": f"unbranded {task['image_type']} of {product_name}, {task['image_style']}, visual intent: {task.get('visual_intent', '')}, clean bakery setting, soft natural light",
                    "prompt_zh": f"{product_name}, {task['image_type']}, {task['image_style']}, visual intent: {task.get('visual_intent', '')}, unbranded bakery scene, soft natural light",
                    "negative_prompt": "logo, text, trademark, official packaging, price tag",
                },
                "compliance_result": {
                    "approved": False,
                    "risk_level": "low",
                    "notes": ["No auto-publishing.", "Generated assets require human review."],
                },
            },
        }
    }


def build_dify_payload(task: dict[str, Any], context_path: Path, max_context_chars: int) -> dict[str, Any]:
    product_knowledge = knowledge_service.build_task_knowledge_context(task, context_path, max_context_chars)
    return {
        "inputs": {
            "product_query": task["product_name"],
            "product_name": task["product_name"],
            "content_type": task["content_type"],
            "image_type": task["image_type"],
            "image_style": task["image_style"],
            "visual_intent": task.get("visual_intent", ""),
            "platforms": task["platforms"],
            "campaign_goal": task["campaign_goal"],
            "audience": task["audience"],
            "constraints": task["constraints"],
            "content_task_json": json.dumps(task, ensure_ascii=False),
            "natural_request": task.get("natural_request", ""),
            "product_knowledge": product_knowledge,
            "brand_context": "Local bakery operation. Use only provided product facts; do not imply external brand authorization.",
            "platform_rules": "No auto-publishing; no health claims; no fake price, inventory, origin, nutrition, logo, trademark, official packaging, or absolute claims.",
            "date": date.today().isoformat(),
        },
        "response_mode": "blocking",
        "user": "local-v2-content-operation",
    }


def validate_dify_outputs(dify_result: dict[str, Any]) -> dict[str, Any]:
    outputs = dify_result.get("data", {}).get("outputs")
    if not isinstance(outputs, dict):
        raise RuntimeError("Dify workflow output must contain data.outputs object.")
    missing = sorted(REQUIRED_DIFY_OUTPUT_KEYS - set(outputs))
    if missing:
        raise RuntimeError(f"Dify workflow output missing required keys: {', '.join(missing)}")
    for key in REQUIRED_DIFY_OUTPUT_KEYS:
        value = parse_json_text(outputs.get(key))
        if not isinstance(value, dict) or not value:
            raise RuntimeError(f"Dify workflow output {key!r} must be a non-empty object.")
    return outputs


def live_image_gate(dify_result: dict[str, Any]) -> tuple[bool, str]:
    outputs = dify_result.get("data", {}).get("outputs", {})
    compliance = parse_json_text(outputs.get("compliance_result", {}))
    if not isinstance(compliance, dict):
        return False, "Compliance result is missing or not structured."
    risk_level = str(compliance.get("risk_level", "")).lower()
    approved = compliance.get("approved")
    if approved is True and risk_level in {"", "low"}:
        return True, ""
    return False, f"Live image blocked by compliance result: approved={approved}, risk_level={risk_level or 'unknown'}."


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one V2.0 content operation for n8n or local production use.")
    parser.add_argument("--mode", choices=["dry-run", "live-dify"], default="dry-run")
    parser.add_argument("--request", default="", help="Plain operator request, for example: 今日的爆品是牛肉恰巴塔，生成它的解构风展示图")
    parser.add_argument("--product-query", default="daily_bakery_product")
    parser.add_argument("--campaign-name", default="Daily Content Operation")
    parser.add_argument("--campaign-goal", default="Generate review-ready Xiaohongshu and Douyin content with multiple image prompts. Video generation is skipped.")
    parser.add_argument("--platform", default="xiaohongshu,douyin")
    parser.add_argument("--content-type", default="daily_product_content")
    parser.add_argument("--image-type", default="product_hero")
    parser.add_argument("--image-style", default="realistic bakery product photography")
    parser.add_argument("--audience", default="local bakery customers")
    parser.add_argument("--constraints", default="No fake price, inventory, sales volume, health claims, nutrition claims, official authorization, logo, trademark, or embedded text.")
    parser.add_argument("--context", default="knowledge/processed/bakery_agent_context.md")
    parser.add_argument("--max-context-chars", type=int, default=4800)
    parser.add_argument("--db", default=str(db_service.DEFAULT_DB.relative_to(ROOT)))
    parser.add_argument("--out-dir", default="runs/operations")
    parser.add_argument("--approval-out-dir", default="runs/approval_queue")
    parser.add_argument("--image-out-dir", default=image_service.DEFAULT_OUT_DIR)
    parser.add_argument("--archive-out-dir", default="runs/operation_archive")
    parser.add_argument("--log", default=str(operation_log_service.DEFAULT_LOG.relative_to(ROOT)))
    parser.add_argument("--live-image", action="store_true")
    parser.add_argument("--skip-image", action="store_true")
    parser.add_argument("--skip-video", action="store_true", default=True)
    parser.add_argument("--image-count", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=240)
    args = parser.parse_args()
    if args.image_count < 1 or args.image_count > MAX_IMAGE_COUNT:
        raise RuntimeError(f"--image-count must be between 1 and {MAX_IMAGE_COUNT}")
    global SELECTED_LOG, ACTIVE_DB
    SELECTED_LOG = args.log
    ACTIVE_DB = args.db

    content_task = build_content_task(args)
    operation_log_service.append_event("operation_started", {**vars(args), "content_task": content_task}, args.log)
    db_service.init_db(args.db)

    campaign = campaign_service.create_campaign(
        {
            "campaign_name": args.campaign_name,
            "product_name": content_task["product_name"],
            "platform": content_task["platforms"],
            "objective": content_task["campaign_goal"],
            "status": "active",
            "notes": (
                f"Created by run_content_operation.py in {args.mode} mode. "
                f"content_type={content_task['content_type']}; "
                f"image_type={content_task['image_type']}; "
                f"image_style={content_task['image_style']}; "
                f"visual_intent={content_task.get('visual_intent', '')}"
            ),
        },
        db_path=args.db,
    )
    content_generation_task = task_service.create_task(
        "content_generation",
        provider="dify" if args.mode == "live-dify" else "local_dry_run",
        input_json=content_task,
        db_path=args.db,
    )
    ACTIVE_TASK_IDS.append(content_generation_task["task_id"])

    context_path = resolve_path(args.context)
    payload = build_dify_payload(content_task, context_path, args.max_context_chars)
    env = load_dotenv(".env")
    if args.mode == "live-dify":
        base_url = env.get("DIFY_BASE_URL") or os.environ.get("DIFY_BASE_URL", "")
        api_key = env.get("DIFY_API_KEY") or os.environ.get("DIFY_API_KEY", "")
        if not base_url or not api_key:
            raise RuntimeError("DIFY_BASE_URL and DIFY_API_KEY are required for --mode live-dify")
        dify_result = dify_client.call_workflow(base_url, api_key, payload, args.timeout)
    else:
        dify_result = dry_run_dify_outputs(content_task)
    outputs = validate_dify_outputs(dify_result)
    live_image_allowed, live_image_block_reason = live_image_gate(dify_result) if args.live_image else (False, "")
    effective_live_image = args.live_image and live_image_allowed

    out_dir = resolve_path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / f"{content_generation_task['task_id']}_dify_output.json"
    write_json(output_path, dify_result)
    content_generation_task = task_service.update_task_status(content_generation_task["task_id"], "succeeded", output_json={"output_path": str(output_path)}, db_path=args.db)

    image_prompt_path = out_dir / f"{content_generation_task['task_id']}_image_prompt.json"
    enhanced_prompt = image_prompt_service.build_enhanced_prompt(outputs, content_task=content_task, source=str(output_path))
    enhanced_prompt["image_count"] = max(1, args.image_count)
    enhanced_prompt["variants"] = image_prompt_service.build_prompt_variants(enhanced_prompt, count=max(1, args.image_count))
    write_json(image_prompt_path, enhanced_prompt)

    approval = approval_service.create_approval_package(
        output_path,
        image_prompt_path,
        out_dir=args.approval_out_dir,
        campaign_id=campaign["campaign_id"],
        product_name=content_task["product_name"],
        platform=content_task["platforms"],
        content_goal=content_task["campaign_goal"],
        content_task=content_task,
    )
    content_generation_task = task_service.link_task_to_approval_package(content_generation_task["task_id"], approval["package_dir"], db_path=args.db)
    task_service.append_task_to_package(approval["package_dir"], content_generation_task)

    image_result: dict[str, Any] = {}
    if not args.skip_image:
        image_task = task_service.create_task(
            "image_generation",
            provider="openai",
            related_package_path=approval["package_dir"],
            input_json={"image_prompt": str(image_prompt_path)},
            db_path=args.db,
        )
        ACTIVE_TASK_IDS.append(image_task["task_id"])
        image_result = image_service.generate_openai_image(image_prompt_path, args.image_out_dir, live=effective_live_image, require_key=effective_live_image, n=max(1, args.image_count))
        if args.live_image and not effective_live_image:
            image_result["live_image_requested"] = True
            image_result["live_image_blocked"] = True
            image_result["live_image_block_reason"] = live_image_block_reason
        approval_service.backfill_asset_result(approval["package_dir"], "image", image_result)
        image_task = task_service.update_task_status(image_task["task_id"], "succeeded", output_json=image_result, db_path=args.db)
        task_service.append_task_to_package(approval["package_dir"], image_task)

    db_service.init_db(args.db)
    with db_service.get_connection(args.db) as conn:
        db_sync_service.sync_package(conn, resolve_path(approval["package_dir"]))
    campaign_service.attach_content_run_to_campaign(campaign["campaign_id"], Path(approval["package_dir"]).name, db_path=args.db)
    package_metadata = approval_service.load_approval_package(approval["package_dir"])["metadata"]
    package_metadata["db_sync_status"] = "synced"
    package_metadata["live_image_requested"] = bool(args.live_image)
    package_metadata["live_image_blocked"] = bool(args.live_image and not effective_live_image)
    if live_image_block_reason:
        package_metadata["live_image_block_reason"] = live_image_block_reason
    package_metadata["updated_at"] = now_iso()
    write_json(Path(approval["package_dir"]) / "metadata.json", package_metadata)
    with db_service.get_connection(args.db) as conn:
        db_sync_service.sync_package(conn, resolve_path(approval["package_dir"]))

    summary = {
        "status": "completed",
        "mode": args.mode,
        "content_task": content_task,
        "campaign_id": campaign["campaign_id"],
        "content_task_id": content_generation_task["task_id"],
        "approval_package": approval["package_dir"],
        "dify_output": str(output_path),
        "image_metadata": image_result.get("metadata_path", ""),
        "image_count": max(1, args.image_count),
        "live_image_requested": bool(args.live_image),
        "live_image_executed": bool(effective_live_image),
        "live_image_blocked": bool(args.live_image and not effective_live_image),
        "live_image_block_reason": live_image_block_reason,
        "video_skipped": args.skip_video,
        "db": str(resolve_path(args.db)),
        "created_at": now_iso(),
    }
    archive = operation_log_service.write_run_archive(Path(approval["package_dir"]).name, summary, args.archive_out_dir)
    summary["operation_archive"] = str(archive)
    operation_log_service.append_event("operation_completed", summary, args.log)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        failed_tasks = []
        for task_id in ACTIVE_TASK_IDS:
            try:
                task = task_service.get_task(task_id, ACTIVE_DB)
                if task and task.get("status") in {"pending", "running"}:
                    failed_tasks.append(task_service.update_task_status(task_id, "failed", error_message=str(exc), db_path=ACTIVE_DB))
            except Exception as task_exc:
                failed_tasks.append({"task_id": task_id, "failure_update_error": str(task_exc)})
        operation_log_service.append_event("operation_failed", {"error": str(exc), "failed_tasks": failed_tasks}, SELECTED_LOG)
        raise
