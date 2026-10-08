from __future__ import annotations

from pathlib import Path
from typing import Any

from . import approval_service, db_service
from .common import now_iso


def validate_asset_metadata(asset: dict[str, Any]) -> bool:
    return bool(asset.get("asset_type") and asset.get("status"))


def register_asset(asset: dict[str, Any], db_path: str | Path = db_service.DEFAULT_DB) -> dict[str, Any]:
    data = {
        "asset_id": asset.get("asset_id") or db_service.make_id("asset"),
        "run_id": asset.get("run_id", ""),
        "task_id": asset.get("task_id", ""),
        "asset_type": asset.get("asset_type", ""),
        "provider": asset.get("provider", ""),
        "prompt": asset.get("prompt", ""),
        "status": asset.get("status", "pending"),
        "local_path": asset.get("local_path", ""),
        "remote_url": asset.get("remote_url", ""),
        "request_json": asset.get("request_json", {}),
        "response_json": asset.get("response_json", {}),
        "error_message": asset.get("error_message", ""),
        "created_at": asset.get("created_at", now_iso()),
        "updated_at": now_iso(),
    }
    if not validate_asset_metadata(data):
        raise RuntimeError("Invalid asset metadata")
    with db_service.get_connection(db_path) as conn:
        db_service.upsert_asset(conn, data)
    return data


def update_asset_status(asset_id: str, status: str, *, response_json: dict[str, Any] | None = None, error_message: str = "", db_path: str | Path = db_service.DEFAULT_DB) -> dict[str, Any]:
    with db_service.get_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM generated_assets WHERE asset_id = ?", (asset_id,)).fetchone()
        if not row:
            raise RuntimeError(f"Asset not found: {asset_id}")
        asset = dict(row)
        asset["status"] = status
        asset["response_json"] = response_json or {}
        asset["error_message"] = error_message
        asset["updated_at"] = now_iso()
        db_service.upsert_asset(conn, asset)
    return asset


def attach_asset_to_approval_package(package_dir: str | Path, asset: dict[str, Any]) -> dict[str, Any]:
    return approval_service.backfill_asset_result(package_dir, asset.get("asset_type", "image"), asset)
