from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .common import display_path, now_iso, parse_json_text, read_json, resolve_path, timestamp, write_json

ALLOWED_STATUSES = {"pending", "approved", "rejected", "needs_revision", "pending_revision_review"}


def load_outputs(path: str | Path) -> dict[str, Any]:
    data = read_json(path, {})
    outputs = data.get("data", {}).get("outputs", {})
    return {key: parse_json_text(value) for key, value in outputs.items()}


def render_block(title: str, value: Any) -> str:
    if value in ("", None, [], {}):
        body = "_empty_"
    elif isinstance(value, (dict, list)):
        body = "```json\n" + json.dumps(value, ensure_ascii=False, indent=2) + "\n```"
    else:
        body = str(value)
    return f"## {title}\n\n{body}\n"


def validate_approval_package(package_dir: str | Path) -> bool:
    path = resolve_path(package_dir)
    required = ["metadata.json", "review.md", "product_flow.md", "enhanced_image_prompt.json", "tasks.json", "assets.json"]
    return path.is_dir() and all((path / item).exists() for item in required)


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) if isinstance(value, (dict, list)) else str(value or "")


def render_product_flow(metadata: dict[str, Any], outputs: dict[str, Any], image_prompt: dict[str, Any]) -> str:
    content_task = metadata.get("content_task", {}) if isinstance(metadata.get("content_task"), dict) else {}
    xhs_copy = outputs.get("xiaohongshu_copy", {})
    douyin_script = outputs.get("douyin_script", {})
    content_plan = outputs.get("content_plan", {})
    compliance = outputs.get("compliance_result", {})
    image_asset = metadata.get("assets", {}).get("image_generation", {}) if isinstance(metadata.get("assets"), dict) else {}
    variants = image_prompt.get("variants", []) if isinstance(image_prompt, dict) else []

    lines = [
        "# Product Operation Flow",
        "",
        "## Task Input",
        "",
        f"- run_id: {metadata.get('run_id', '')}",
        f"- product_name: {metadata.get('product_name', '')}",
        f"- natural_request: {content_task.get('natural_request', '')}",
        f"- content_type: {content_task.get('content_type', '')}",
        f"- image_type: {content_task.get('image_type', '')}",
        f"- image_style: {content_task.get('image_style', '')}",
        f"- visual_intent: {content_task.get('visual_intent', '')}",
        f"- platform: {metadata.get('platform', '')}",
        f"- approval_status: {metadata.get('approval_status', metadata.get('status', ''))}",
        f"- image_status: {metadata.get('image_status', '')}",
        f"- publish_status: {metadata.get('publish_status', 'not_started')}",
        f"- publish_draft_path: {metadata.get('publish_draft_path', '')}",
        "",
        "## Content Plan",
        "",
        compact_json(content_plan),
        "",
        "## Xiaohongshu Output",
        "",
        compact_json(xhs_copy),
        "",
        "## Douyin Output",
        "",
        compact_json(douyin_script),
        "",
        "## Image Generation Plan",
        "",
        f"- product_query: {image_prompt.get('product_query', '') if isinstance(image_prompt, dict) else ''}",
        f"- aspect_ratio: {image_prompt.get('aspect_ratio', '') if isinstance(image_prompt, dict) else ''}",
        f"- variant_count: {len(variants)}",
        f"- asset_status: {image_asset.get('status', '')}",
        f"- asset_metadata: {image_asset.get('metadata_path', '')}",
        f"- selected_image_id: {image_asset.get('selected_image_id', metadata.get('selected_image_id', ''))}",
        "",
    ]
    if variants:
        for variant in variants:
            lines.extend(
                [
                    f"### {variant.get('variant_id', 'variant')}",
                    "",
                    f"- title: {variant.get('title', '')}",
                    f"- status: {variant.get('status', '')}",
                    f"- review_status: {variant.get('review_status', '')}",
                    f"- selected: {variant.get('selected', False)}",
                    f"- aspect_ratio: {variant.get('aspect_ratio', '')}",
                    "",
                    "Prompt EN:",
                    "",
                    str(variant.get("prompt_en", "")),
                    "",
                ]
            )
    else:
        lines.extend(["_No image variants prepared._", ""])
    lines.extend(
        [
            "## Compliance",
            "",
            compact_json(compliance),
            "",
            "## Review Decision",
            "",
            "- [ ] Approve",
            "- [ ] Needs revision",
            "- [ ] Reject",
            "",
            "## Reviewer Notes",
            "",
            "- ",
        ]
    )
    return "\n".join(lines)


def write_product_flow(package_dir: str | Path, metadata: dict[str, Any] | None = None, outputs: dict[str, Any] | None = None, image_prompt: dict[str, Any] | None = None) -> Path:
    path = resolve_path(package_dir)
    metadata = metadata or read_json(path / "metadata.json", {})
    if outputs is None:
        source_output = metadata.get("source_output", "")
        outputs = load_outputs(resolve_path(source_output)) if source_output else {}
    image_prompt = image_prompt if image_prompt is not None else read_json(path / "enhanced_image_prompt.json", {})
    flow_path = path / "product_flow.md"
    flow_path.write_text(render_product_flow(metadata, outputs or {}, image_prompt or {}), encoding="utf-8")
    return flow_path


def reserve_run_dir(out_dir: str | Path) -> tuple[str, Path]:
    base_dir = resolve_path(out_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    base_run_id = f"run_{timestamp()}"
    for index in range(100):
        run_id = base_run_id if index == 0 else f"{base_run_id}_{index:02d}"
        package_dir = base_dir / run_id
        try:
            package_dir.mkdir(exist_ok=False)
            return run_id, package_dir
        except FileExistsError:
            continue
    raise RuntimeError(f"Could not reserve unique approval package directory under {base_dir}")


def create_approval_package(
    input_path: str | Path = "runs/bakery_latest_output.json",
    image_prompt_path: str | Path = "runs/bakery_latest_image_prompt.json",
    out_dir: str | Path = "runs/approval_queue",
    *,
    campaign_id: str = "",
    product_name: str = "bakery product",
    platform: str = "xiaohongshu,douyin",
    content_task: dict[str, Any] | None = None,
    content_goal: str = "Generate review-ready bakery content",
    task_records: list[dict[str, Any]] | None = None,
) -> dict[str, str]:
    source_path = resolve_path(input_path)
    prompt_path = resolve_path(image_prompt_path)
    outputs = load_outputs(source_path)
    image_prompt = read_json(prompt_path, {})

    run_id, package_dir = reserve_run_dir(out_dir)

    metadata = {
        "run_id": run_id,
        "campaign_id": campaign_id,
        "agent_name": "Bakery AI Operation Agent V2",
        "product_name": product_name,
        "platform": platform,
        "content_goal": content_goal,
        "content_task": content_task or {},
        "approval_status": "pending",
        "image_status": "not_started",
        "video_status": "skipped",
        "db_sync_status": "not_started",
        "status": "pending",
        "source_output": display_path(source_path),
        "source_image_prompt": display_path(prompt_path),
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "assets": {
            "image_generation": {"status": "not_started", "review_status": "pending", "image_paths": []},
            "video_generation": {"status": "skipped", "review_status": "future", "video_paths": []},
        },
        "review_checklist": [
            "Copy matches the bakery brand tone and does not imply external official authorization.",
            "No fake price, inventory, origin, ingredients, nutrition, sales volume, or health claims.",
            "Image prompt blocks logos, trademarks, embedded text, official packaging, and misleading brand assets.",
            "Generated image, if present, is free of logos, text, trademarks, official packaging, and misleading claims.",
            "Video generation is intentionally skipped in V2 image-first operation.",
            "Rewrite if store-specific activity details are missing or uncertain.",
        ],
        "output_keys": sorted(outputs.keys()),
    }

    write_json(package_dir / "metadata.json", metadata)
    write_json(package_dir / "enhanced_image_prompt.json", image_prompt)
    write_json(package_dir / "tasks.json", task_records or [])
    write_json(package_dir / "assets.json", [])
    write_json(package_dir / "revision_requests.json", [])
    (package_dir / "revisions").mkdir(exist_ok=True)
    product_flow = write_product_flow(package_dir, metadata, outputs, image_prompt)

    sections = [
        "# Approval Package",
        "",
        f"- agent_name: {metadata['agent_name']}",
        f"- run_id: {run_id}",
        f"- campaign_id: {campaign_id}",
        f"- product_name: {product_name}",
        f"- platform: {platform}",
        f"- content_type: {(content_task or {}).get('content_type', '')}",
        f"- image_type: {(content_task or {}).get('image_type', '')}",
        f"- image_style: {(content_task or {}).get('image_style', '')}",
        "- approval_status: pending",
        "",
        "## Content Summary",
        "",
        str(outputs.get("content_plan", "")),
        "",
        render_block("Xiaohongshu Copy", outputs.get("xiaohongshu_copy")),
        render_block("Douyin Script", outputs.get("douyin_script")),
        render_block("Image Prompt", image_prompt),
        render_block("Compliance Result", outputs.get("compliance_result")),
        "## Current Task Status",
        "",
        "- image_generation: not_started",
        "- video_generation: skipped",
        "- db_sync: not_started",
        "",
        "## Review Checklist",
        "",
    ]
    sections.extend(f"- [ ] {item}" for item in metadata["review_checklist"])
    sections.extend(["", "## Manual Notes", "", "- "])
    (package_dir / "review.md").write_text("\n".join(sections), encoding="utf-8")

    return {"package_dir": str(package_dir), "metadata": str(package_dir / "metadata.json"), "review": str(package_dir / "review.md"), "product_flow": str(product_flow)}


def load_approval_package(package_dir: str | Path) -> dict[str, Any]:
    path = resolve_path(package_dir)
    return {
        "package_dir": str(path),
        "metadata": read_json(path / "metadata.json", {}),
        "tasks": read_json(path / "tasks.json", []),
        "assets": read_json(path / "assets.json", []),
        "revision_requests": read_json(path / "revision_requests.json", []),
    }


def append_review_note(package_dir: str | Path, status: str, note: str) -> None:
    path = resolve_path(package_dir)
    review_path = path / "review.md"
    text = review_path.read_text(encoding="utf-8") if review_path.exists() else "# Approval Package\n"
    if "## Manual Notes" not in text:
        text = text.rstrip() + "\n\n## Manual Notes\n"
    text = text.rstrip() + f"\n- {now_iso()} status={status}\n  note: {note}\n"
    review_path.write_text(text, encoding="utf-8")


def update_approval_status(package_dir: str | Path, status: str, note: str = "") -> dict[str, str]:
    if status not in ALLOWED_STATUSES:
        raise RuntimeError(f"Invalid approval status: {status}")
    path = resolve_path(package_dir)
    metadata = read_json(path / "metadata.json", {})
    metadata["status"] = status
    metadata["approval_status"] = status
    metadata["updated_at"] = now_iso()
    if note:
        metadata.setdefault("review_notes", []).append({"created_at": metadata["updated_at"], "status": status, "note": note})
    write_json(path / "metadata.json", metadata)
    write_product_flow(path, metadata)
    append_review_note(path, status, note)
    return {"package_dir": str(path), "status": status, "metadata": str(path / "metadata.json"), "review": str(path / "review.md")}


def backfill_asset_result(package_dir: str | Path, asset_type: str, asset_result: dict[str, Any]) -> dict[str, Any]:
    path = resolve_path(package_dir)
    metadata = read_json(path / "metadata.json", {})
    assets_obj = metadata.setdefault("assets", {})
    key = f"{asset_type}_generation"
    current = assets_obj.setdefault(key, {})
    current.update(asset_result)
    current["updated_at"] = now_iso()
    metadata[f"{asset_type}_status"] = current.get("status", "prepared")
    metadata["updated_at"] = now_iso()
    write_json(path / "metadata.json", metadata)
    write_product_flow(path, metadata)

    assets = read_json(path / "assets.json", [])
    assets.append({"asset_type": asset_type, **asset_result, "updated_at": current["updated_at"]})
    write_json(path / "assets.json", assets)

    review_path = path / "review.md"
    if review_path.exists():
        text = review_path.read_text(encoding="utf-8")
        section = (
            f"## Generated Assets\n\n"
            f"- {asset_type.capitalize()} generation status: {current.get('status', '')}\n"
            f"- {asset_type.capitalize()} metadata: {current.get('metadata_path', '')}\n"
            f"- {asset_type.capitalize()} review status: {current.get('review_status', 'pending')}\n\n"
        )
        if "## Generated Assets" in text and "## Review Checklist" in text:
            before, rest = text.split("## Generated Assets", 1)
            _, after = rest.split("## Review Checklist", 1)
            text = before.rstrip() + "\n\n" + section + "## Review Checklist" + after
        elif "## Current Task Status" in text:
            text = text.replace("## Current Task Status", section + "## Current Task Status", 1)
        else:
            text = text.rstrip() + "\n\n" + section
        review_path.write_text(text, encoding="utf-8")
    return current
