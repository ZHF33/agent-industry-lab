from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import approval_service, db_service, db_sync_service, task_service
from .common import now_iso, parse_json_text, read_json, resolve_path, write_json

PUBLISH_TASK_TYPE = "manual_publish_record"
LEGACY_PUBLISH_TASK_TYPES = {"publish_placeholder"}


def _require_ready(metadata: dict[str, Any], package_path: Path) -> None:
    status = metadata.get("approval_status", metadata.get("status", ""))
    if status != "approved":
        raise RuntimeError(f"Publish draft requires approved package status, got {status!r}.")
    image_asset = metadata.get("assets", {}).get("image_generation", {})
    if not image_asset.get("selected_image_id") and not metadata.get("selected_image_id"):
        raise RuntimeError("Publish draft requires a selected image variant.")
    if not (package_path / "enhanced_image_prompt.json").exists():
        raise RuntimeError(f"Enhanced image prompt not found: {package_path / 'enhanced_image_prompt.json'}")


def _require_source_outputs(metadata: dict[str, Any], outputs: dict[str, Any], platforms: list[str]) -> None:
    source = str(metadata.get("source_output", "")).strip()
    if not source:
        raise RuntimeError("Publish draft requires source_output metadata.")
    if not outputs:
        raise RuntimeError(f"Publish draft source output is missing or empty: {source}")
    required_by_platform = {
        "xiaohongshu": "xiaohongshu_copy",
        "douyin": "douyin_script",
    }
    missing = [key for platform, key in required_by_platform.items() if platform in platforms and not parse_json_text(outputs.get(key, {}))]
    if missing:
        raise RuntimeError(f"Publish draft requires non-empty platform outputs: {', '.join(sorted(missing))}")


def _selected_image(metadata: dict[str, Any]) -> dict[str, Any]:
    image_asset = metadata.get("assets", {}).get("image_generation", {})
    selected_id = image_asset.get("selected_image_id") or metadata.get("selected_image_id", "")
    selected = image_asset.get("selected_image") or metadata.get("selected_image") or {}
    if selected:
        return selected
    for image in image_asset.get("images", []):
        if str(image.get("image_id", "")) == str(selected_id):
            return image
    return {}


def _require_selected_image(metadata: dict[str, Any], selected: dict[str, Any]) -> None:
    if not selected:
        raise RuntimeError("Publish draft requires selected image details.")
    image_id = str(selected.get("image_id", "")).strip()
    selected_id = str(metadata.get("assets", {}).get("image_generation", {}).get("selected_image_id") or metadata.get("selected_image_id", "")).strip()
    if selected_id and image_id and image_id != selected_id:
        raise RuntimeError(f"Selected image metadata mismatch: selected_image_id={selected_id!r}, image_id={image_id!r}.")
    status = str(selected.get("status", "")).strip()
    review_status = str(selected.get("review_status", "")).strip()
    if status not in {"prepared", "completed", "generated", "selected"}:
        raise RuntimeError(f"Publish draft selected image has invalid status: {status!r}.")
    if review_status and review_status != "selected":
        raise RuntimeError(f"Publish draft selected image has invalid review_status: {review_status!r}.")


def _platform_list(platform: str) -> list[str]:
    values = [item.strip() for item in str(platform or "").split(",") if item.strip()]
    return values or ["xiaohongshu"]


def _published_platforms(metadata: dict[str, Any]) -> list[str]:
    records = metadata.get("publish_records", [])
    if not isinstance(records, list):
        return []
    platforms: list[str] = []
    for record in records:
        if isinstance(record, dict):
            platform = str(record.get("platform", "")).strip()
            if platform and platform not in platforms:
                platforms.append(platform)
    return platforms


def _pending_publish_platforms(metadata: dict[str, Any]) -> list[str]:
    published = set(_published_platforms(metadata))
    return [platform for platform in _platform_list(metadata.get("platform", "")) if platform not in published]


def _publish_status_from_records(metadata: dict[str, Any]) -> str:
    return "published" if not _pending_publish_platforms(metadata) else "partially_published"


def _platform_payload(platform: str, outputs: dict[str, Any]) -> dict[str, Any]:
    if platform == "xiaohongshu":
        copy = parse_json_text(outputs.get("xiaohongshu_copy", {}))
        return copy if isinstance(copy, dict) else {"body": str(copy)}
    if platform == "douyin":
        script = parse_json_text(outputs.get("douyin_script", {}))
        return script if isinstance(script, dict) else {"script": str(script)}
    return {"note": "No platform-specific writer configured yet."}


def build_publish_draft(package_dir: str | Path, *, out_dir: str | Path = "runs/publish_drafts") -> dict[str, Any]:
    package_path = resolve_path(package_dir)
    metadata = read_json(package_path / "metadata.json", {})
    if not metadata:
        raise RuntimeError(f"Approval package metadata not found: {package_path}")
    _require_ready(metadata, package_path)
    outputs = approval_service.load_outputs(resolve_path(metadata.get("source_output", ""))) if metadata.get("source_output") else {}
    platforms = _platform_list(metadata.get("platform", ""))
    _require_source_outputs(metadata, outputs, platforms)
    selected = _selected_image(metadata)
    _require_selected_image(metadata, selected)
    platform_drafts = {platform: _platform_payload(platform, outputs) for platform in platforms}
    created_at = now_iso()
    draft = {
        "draft_id": f"{metadata.get('run_id', package_path.name)}_publish_draft",
        "status": "prepared",
        "run_id": metadata.get("run_id", package_path.name),
        "package_dir": str(package_path),
        "product_name": metadata.get("product_name", ""),
        "platforms": platforms,
        "content_goal": metadata.get("content_goal", ""),
        "selected_image_id": selected.get("image_id", metadata.get("selected_image_id", "")),
        "selected_image": selected,
        "platform_drafts": platform_drafts,
        "compliance_result": parse_json_text(outputs.get("compliance_result", {})),
        "manual_publish_required": True,
        "publish_instruction": "Manual publishing only. Verify copy, selected image, platform rules, and store facts before posting.",
        "created_at": created_at,
        "updated_at": created_at,
    }
    out = resolve_path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    draft_path = out / f"{draft['draft_id']}.json"
    write_json(draft_path, draft)
    write_json(package_path / "publish_draft.json", draft)
    (package_path / "publish_draft.md").write_text(render_publish_draft_markdown(draft), encoding="utf-8")
    return {**draft, "draft_path": str(draft_path), "package_draft_path": str(package_path / "publish_draft.json")}


def render_publish_draft_markdown(draft: dict[str, Any]) -> str:
    lines = [
        "# Publish Draft",
        "",
        f"- draft_id: {draft.get('draft_id', '')}",
        f"- run_id: {draft.get('run_id', '')}",
        f"- product_name: {draft.get('product_name', '')}",
        f"- status: {draft.get('status', '')}",
        f"- selected_image_id: {draft.get('selected_image_id', '')}",
        f"- manual_publish_required: {draft.get('manual_publish_required', True)}",
        "",
        "## Selected Image",
        "",
        f"- provider: {draft.get('selected_image', {}).get('provider', '')}",
        f"- status: {draft.get('selected_image', {}).get('status', '')}",
        f"- metadata_path: {draft.get('selected_image', {}).get('metadata_path', '')}",
        f"- image_paths: {draft.get('selected_image', {}).get('image_paths', [])}",
        "",
        "## Platform Drafts",
        "",
    ]
    for platform, payload in draft.get("platform_drafts", {}).items():
        lines.extend(
            [
                f"### {platform}",
                "",
                "```json",
                json.dumps(payload, ensure_ascii=False, indent=2),
                "```",
                "",
            ]
        )
    lines.extend(
        [
            "## Compliance",
            "",
            "```json",
            json.dumps(draft.get("compliance_result", {}), ensure_ascii=False, indent=2),
            "```",
            "",
            "## Manual Checklist",
            "",
            "- [ ] Copy checked against platform rules.",
            "- [ ] Selected image checked for logos, text, trademarks, official packaging, and misleading claims.",
            "- [ ] Store-specific facts checked manually.",
            "- [ ] Manual publisher confirms final post destination.",
            "",
        ]
    )
    return "\n".join(lines)


def prepare_publish_draft(
    package_dir: str | Path,
    *,
    out_dir: str | Path = "runs/publish_drafts",
    db: str | Path = db_service.DEFAULT_DB,
    sync_db: bool = True,
) -> dict[str, Any]:
    package_path = resolve_path(package_dir)
    draft = build_publish_draft(package_path, out_dir=out_dir)
    metadata = read_json(package_path / "metadata.json", {})
    metadata["publish_status"] = "draft_prepared"
    metadata["publish_draft_path"] = draft["package_draft_path"]
    metadata["updated_at"] = now_iso()
    metadata.setdefault("review_notes", []).append(
        {
            "created_at": metadata["updated_at"],
            "status": "publish_draft_prepared",
            "note": f"Prepared manual publish draft: {draft['package_draft_path']}",
        }
    )
    write_json(package_path / "metadata.json", metadata)
    approval_service.append_review_note(package_path, "publish_draft_prepared", f"Prepared manual publish draft: {draft['package_draft_path']}")
    approval_service.write_product_flow(package_path, metadata)
    run_id = metadata.get("run_id", package_path.name)
    existing_publish_task = next(
        (
            task
            for task in read_json(package_path / "tasks.json", [])
            if isinstance(task, dict) and task.get("task_type") in {PUBLISH_TASK_TYPE, *LEGACY_PUBLISH_TASK_TYPES} and task.get("related_run_id") == run_id
        ),
        {},
    )
    if existing_publish_task.get("task_id"):
        publish_task = {**existing_publish_task}
        publish_task.update(
            {
                "status": "pending",
                "task_type": PUBLISH_TASK_TYPE,
                "provider": "manual",
                "related_run_id": run_id,
                "related_package_path": str(package_path),
                "input_json": {"publish_draft": draft["package_draft_path"], "manual_publish_required": True},
                "updated_at": now_iso(),
            }
        )
        with db_service.get_connection(db) as conn:
            db_service.upsert_task(conn, publish_task)
    else:
        publish_task = task_service.create_task(
            PUBLISH_TASK_TYPE,
            provider="manual",
            related_run_id=run_id,
            related_package_path=str(package_path),
            input_json={"publish_draft": draft["package_draft_path"], "manual_publish_required": True},
            db_path=db,
        )
    publish_task = task_service.update_task_status(publish_task["task_id"], "succeeded", output_json=draft, db_path=db)
    tasks = read_json(package_path / "tasks.json", [])
    tasks = [
        task
        for task in tasks
        if not (
            isinstance(task, dict)
            and task.get("task_type") in LEGACY_PUBLISH_TASK_TYPES
            and task.get("related_run_id") == run_id
        )
    ]
    write_json(package_path / "tasks.json", tasks)
    task_service.upsert_unique_task_to_package(package_path, publish_task, ["task_type", "related_run_id"])
    synced = False
    if sync_db:
        with db_service.get_connection(db) as conn:
            synced = db_sync_service.sync_package(conn, package_path)
    return {
        "status": "draft_prepared",
        "run_id": metadata.get("run_id", package_path.name),
        "package_dir": str(package_path),
        "draft_path": draft["draft_path"],
        "package_draft_path": draft["package_draft_path"],
        "selected_image_id": draft["selected_image_id"],
        "platforms": draft["platforms"],
        "task_id": publish_task["task_id"],
        "db_sync_status": "synced" if synced else "skipped",
        "db": str(resolve_path(db)),
    }


def record_manual_publish(
    package_dir: str | Path,
    *,
    platform: str,
    published_url: str = "",
    note: str = "",
    db: str | Path = db_service.DEFAULT_DB,
    published_at: str = "",
    metrics: dict[str, Any] | None = None,
    sync_db: bool = True,
) -> dict[str, Any]:
    package_path = resolve_path(package_dir)
    metadata = read_json(package_path / "metadata.json", {})
    if not metadata:
        raise RuntimeError(f"Approval package metadata not found: {package_path}")
    if metadata.get("publish_status") not in {"draft_prepared", "partially_published", "published"} or not (package_path / "publish_draft.json").exists():
        raise RuntimeError("Manual publish record requires a prepared publish draft.")
    platform = str(platform or "").strip()
    if not platform:
        raise RuntimeError("platform is required")
    metrics = metrics or {}
    now = now_iso()
    record = {
        "run_id": metadata.get("run_id", package_path.name),
        "campaign_id": metadata.get("campaign_id", ""),
        "platform": platform,
        "published_at": published_at or now,
        "published_url": published_url,
        "note": note,
        "metrics": {
            "impressions": int(metrics.get("impressions") or 0),
            "likes": int(metrics.get("likes") or 0),
            "saves": int(metrics.get("saves") or 0),
            "comments": int(metrics.get("comments") or 0),
        },
        "created_at": now,
        "updated_at": now,
    }
    records = metadata.setdefault("publish_records", [])
    replaced = False
    for index, existing in enumerate(records):
        if isinstance(existing, dict) and existing.get("platform") == platform:
            records[index] = {**existing, **record, "created_at": existing.get("created_at", now), "updated_at": now}
            record = records[index]
            replaced = True
            break
    if not replaced:
        records.append(record)
    metadata["publish_status"] = _publish_status_from_records(metadata)
    metadata["published_at"] = record["published_at"]
    metadata["updated_at"] = now
    metadata.setdefault("review_notes", []).append(
        {
            "created_at": now,
            "status": "published",
            "note": note or f"Manual publish recorded for {platform}.",
            "platform": platform,
            "published_url": published_url,
        }
    )
    write_json(package_path / "metadata.json", metadata)
    write_json(package_path / "publish_record.json", {"records": records, "updated_at": now})
    approval_service.append_review_note(package_path, "published", note or f"Manual publish recorded for {platform}.")
    approval_service.write_product_flow(package_path, metadata)

    history_id = ""
    if sync_db:
        with db_service.get_connection(db) as conn:
            history_id = db_service.upsert_campaign_history(
                conn,
                {
                    "history_id": f"{record['run_id']}_{platform}_publish",
                    "campaign_id": record["campaign_id"],
                    "run_id": record["run_id"],
                    "platform": platform,
                    "published_at": record["published_at"],
                    **record["metrics"],
                    "conversion_notes": note or published_url,
                    "created_at": record["created_at"],
                    "updated_at": record["updated_at"],
                },
            )
            db_sync_service.sync_package(conn, package_path)
    return {
        "status": metadata["publish_status"],
        "run_id": record["run_id"],
        "package_dir": str(package_path),
        "platform": platform,
        "published_platforms": _published_platforms(metadata),
        "pending_platforms": _pending_publish_platforms(metadata),
        "published_url": published_url,
        "published_at": record["published_at"],
        "history_id": history_id,
        "db": str(resolve_path(db)),
    }
