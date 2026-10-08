#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.common import ROOT, read_json

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def normalize_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def load_package_summary(path: Path) -> dict[str, Any]:
    metadata = read_json(path / "metadata.json", {})
    image_asset = metadata.get("assets", {}).get("image_generation", {})
    images = image_asset.get("images") if isinstance(image_asset, dict) else []
    selected_image = image_asset.get("selected_image", {}) if isinstance(image_asset, dict) else {}
    selected_paths = selected_image.get("image_paths", []) if isinstance(selected_image, dict) else []
    image_ids = [str(image.get("image_id", "")) for image in images if isinstance(image, dict) and image.get("image_id")] if isinstance(images, list) else []
    image_has_files = any(bool(image.get("image_paths")) for image in images if isinstance(image, dict)) if isinstance(images, list) else False
    publish_records = metadata.get("publish_records", [])
    published_platforms = []
    if isinstance(publish_records, list):
        for record in publish_records:
            if isinstance(record, dict):
                platform = str(record.get("platform", "")).strip()
                if platform and platform not in published_platforms:
                    published_platforms.append(platform)
    configured_platforms = [item.strip() for item in str(metadata.get("platform", "")).split(",") if item.strip()] or ["xiaohongshu"]
    pending_publish_platforms = [platform for platform in configured_platforms if platform not in set(published_platforms)]
    return {
        "run_id": metadata.get("run_id", path.name),
        "package_dir": normalize_path(path),
        "status": metadata.get("approval_status", metadata.get("status", "")),
        "product_name": metadata.get("product_name", ""),
        "platform": metadata.get("platform", ""),
        "content_type": metadata.get("content_task", {}).get("content_type", ""),
        "image_type": metadata.get("content_task", {}).get("image_type", ""),
        "image_status": metadata.get("image_status", ""),
        "image_count": len(images) if isinstance(images, list) else 0,
        "image_ids": image_ids,
        "image_has_files": image_has_files,
        "image_review_status": metadata.get("image_review_status", image_asset.get("review_status", "") if isinstance(image_asset, dict) else ""),
        "selected_image_id": image_asset.get("selected_image_id", metadata.get("selected_image_id", "")) if isinstance(image_asset, dict) else metadata.get("selected_image_id", ""),
        "selected_image_has_file": bool(selected_paths),
        "publish_status": metadata.get("publish_status", ""),
        "publish_draft_path": metadata.get("publish_draft_path", ""),
        "publish_record_count": len(publish_records) if isinstance(publish_records, list) else 0,
        "published_platforms": published_platforms,
        "pending_publish_platforms": pending_publish_platforms,
        "created_at": metadata.get("created_at", ""),
        "updated_at": metadata.get("updated_at", ""),
        "review_note_count": len(metadata.get("review_notes", [])),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="List local approval packages for human review.")
    parser.add_argument("--queue", default="runs/approval_queue", help="Approval queue directory.")
    parser.add_argument("--status", default="", help="Filter by approval status, for example pending or needs_revision.")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    queue = Path(args.queue)
    if not queue.is_absolute():
        queue = ROOT / queue
    packages = sorted([p for p in queue.glob("run_*") if p.is_dir()], key=lambda p: p.stat().st_mtime, reverse=True) if queue.exists() else []
    rows = [load_package_summary(path) for path in packages]
    if args.status:
        rows = [row for row in rows if row["status"] == args.status]
    rows = rows[: args.limit]
    result = {"approval_queue": normalize_path(queue), "count": len(rows), "packages": rows}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for row in rows:
            print(f"{row['updated_at']}  {row['status']:<22} {row['product_name']:<20} {row['package_dir']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
