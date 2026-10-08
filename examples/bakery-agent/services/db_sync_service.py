from __future__ import annotations

import hashlib
from pathlib import Path

from . import db_service
from .common import read_json, resolve_path


def load_packages(package_dir: str) -> list[Path]:
    if package_dir:
        return [resolve_path(package_dir)]
    queue = resolve_path("runs/approval_queue")
    return sorted(queue.glob("run_*")) if queue.exists() else []


def sync_package(conn, package_dir: Path) -> bool:
    metadata = read_json(package_dir / "metadata.json", {})
    if not metadata:
        return False
    run_id = metadata.get("run_id") or metadata.get("package_id") or package_dir.name
    campaign_id = metadata.get("campaign_id", "")
    if campaign_id:
        db_service.upsert_campaign(
            conn,
            {
                "campaign_id": campaign_id,
                "campaign_name": metadata.get("campaign_name", campaign_id),
                "product_name": metadata.get("product_name", ""),
                "platform": metadata.get("platform", ""),
                "objective": metadata.get("content_goal", ""),
                "status": "active",
                "created_at": metadata.get("created_at", ""),
                "updated_at": metadata.get("updated_at", metadata.get("created_at", "")),
            },
        )
    db_service.upsert_content_run(
        conn,
        {
            "run_id": run_id,
            "campaign_id": campaign_id,
            "product_name": metadata.get("product_name", ""),
            "platform": metadata.get("platform", ""),
            "content_goal": metadata.get("content_goal", ""),
            "dify_status": metadata.get("dify_status", ""),
            "approval_status": metadata.get("approval_status", metadata.get("status", "")),
            "package_path": str(package_dir),
            "created_at": metadata.get("created_at", ""),
            "updated_at": metadata.get("updated_at", ""),
            "raw_output_json": metadata,
        },
    )
    for asset_type, asset in metadata.get("assets", {}).items():
        if asset_type == "image_generation" and isinstance(asset.get("images"), list) and asset["images"]:
            for image in asset["images"]:
                paths = image.get("image_paths") or []
                image_id = image.get("image_id") or f"image_{len(paths)}"
                db_service.upsert_asset(
                    conn,
                    {
                        "asset_id": image.get("asset_id") or f"{run_id}_image_{image_id}",
                        "run_id": run_id,
                        "asset_type": "image",
                        "provider": image.get("provider", asset.get("provider", "")),
                        "prompt": image.get("prompt", ""),
                        "status": image.get("review_status") or image.get("status", asset.get("status", "")),
                        "local_path": paths[0] if paths else "",
                        "request_json": image.get("request_payload", {}),
                        "response_json": image,
                        "error_message": image.get("error_message", asset.get("error_message", "")),
                        "created_at": image.get("created_at", metadata.get("created_at", "")),
                        "updated_at": image.get("updated_at", asset.get("updated_at", metadata.get("updated_at", ""))),
                    },
                )
            continue
        paths = asset.get("image_paths") or asset.get("video_paths") or []
        db_service.upsert_asset(
            conn,
            {
                "asset_id": asset.get("asset_id") or f"{run_id}_{asset_type}",
                "run_id": run_id,
                "asset_type": asset_type.replace("_generation", ""),
                "provider": asset.get("provider", ""),
                "prompt": asset.get("prompt", ""),
                "status": asset.get("status", ""),
                "local_path": paths[0] if paths else "",
                "request_json": asset.get("request_payload", {}),
                "response_json": asset,
                "error_message": asset.get("error_message", ""),
                "created_at": metadata.get("created_at", ""),
                "updated_at": asset.get("updated_at", metadata.get("updated_at", "")),
            },
        )
    for review in metadata.get("review_notes", []):
        review_fingerprint = "|".join(
            [
                run_id,
                str(review.get("created_at", "")),
                str(review.get("status", metadata.get("approval_status", ""))),
                str(review.get("note", "")),
            ]
        )
        db_service.upsert_approval_review(
            conn,
            {
                "review_id": f"{run_id}_review_{hashlib.sha1(review_fingerprint.encode('utf-8')).hexdigest()[:12]}",
                "run_id": run_id,
                "package_path": str(package_dir),
                "status": review.get("status", metadata.get("approval_status", "")),
                "reviewer_note": review.get("note", ""),
                "risk_level": review.get("risk_level", ""),
                "created_at": review.get("created_at", ""),
                "updated_at": review.get("created_at", ""),
            },
        )
    return True
