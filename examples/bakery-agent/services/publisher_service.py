from __future__ import annotations

from pathlib import Path
from typing import Any

from . import publish_service
from .common import load_dotenv, now_iso, read_json, resolve_path

SUPPORTED_PLATFORMS = {"xiaohongshu", "douyin"}
LIVE_REQUIRED_ENV = {
    "xiaohongshu": ["XIAOHONGSHU_PUBLISH_ENABLED", "XIAOHONGSHU_PUBLISH_TOKEN"],
    "douyin": ["DOUYIN_PUBLISH_ENABLED", "DOUYIN_PUBLISH_TOKEN"],
}


def _truthy(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _platforms(value: str) -> list[str]:
    return [item.strip() for item in str(value or "").split(",") if item.strip()] or ["xiaohongshu"]


def connector_readiness(env_file: str | Path = ".env", platforms: list[str] | None = None) -> dict[str, Any]:
    env = load_dotenv(env_file)
    requested = platforms or ["xiaohongshu", "douyin"]
    mode = (env.get("PUBLISH_CONNECTOR_MODE") or "manual").strip().lower()
    mock_enabled = _truthy(env.get("MOCK_PUBLISH_ENABLED", ""))
    platform_reports: dict[str, Any] = {}
    for platform in requested:
        blockers: list[str] = []
        if platform not in SUPPORTED_PLATFORMS:
            blockers.append(f"Unsupported publish platform: {platform}")
        required = LIVE_REQUIRED_ENV.get(platform, [])
        missing = [key for key in required if not env.get(key)]
        enabled_key = required[0] if required else ""
        live_enabled = _truthy(env.get(enabled_key, "")) if enabled_key else False
        if not live_enabled:
            blockers.append(f"{enabled_key or platform + '_PUBLISH_ENABLED'} is not enabled")
        if missing:
            blockers.append(f"Missing live publish env keys: {', '.join(missing)}")
        blockers.append("Live publisher implementation is not connected yet; use manual record or mock mode.")
        platform_reports[platform] = {
            "live_ready": False,
            "blockers": blockers,
            "required_env": required,
            "mock_ready": mock_enabled and platform in SUPPORTED_PLATFORMS,
        }
    return {
        "mode": mode,
        "manual_record_ready": True,
        "mock_ready": mock_enabled,
        "live_ready": False,
        "platforms": platform_reports,
        "blockers": [
            "External platform live publishing is not enabled.",
            "Live publisher implementation is intentionally not connected until credentials, platform policy review, rate limits, and rollback/audit procedures are in place.",
        ],
    }


def mock_publish(
    package_dir: str | Path,
    *,
    platform: str,
    db: str | Path = publish_service.db_service.DEFAULT_DB,
    env_file: str | Path = ".env",
    sync_db: bool = True,
) -> dict[str, Any]:
    readiness = connector_readiness(env_file, [platform])
    if not readiness["mock_ready"]:
        raise RuntimeError("Mock publish is disabled. Set MOCK_PUBLISH_ENABLED=true for safe connector testing.")
    platform_report = readiness["platforms"].get(platform, {})
    if not platform_report.get("mock_ready"):
        raise RuntimeError(f"Mock publish is not available for platform: {platform}")
    package_path = resolve_path(package_dir)
    draft = read_json(package_path / "publish_draft.json", {})
    if not draft:
        raise RuntimeError("Mock publish requires publish_draft.json.")
    run_id = draft.get("run_id", package_path.name)
    mock_url = f"https://mock.local/{platform}/{run_id}"
    return {
        "mode": "mock",
        "platform": platform,
        "mock_url": mock_url,
        "publish_record": publish_service.record_manual_publish(
            package_path,
            platform=platform,
            published_url=mock_url,
            note=f"Mock publish connector verification at {now_iso()}.",
            db=db,
            sync_db=sync_db,
        ),
    }


def package_publish_connector_status(package_dir: str | Path, *, env_file: str | Path = ".env") -> dict[str, Any]:
    package_path = resolve_path(package_dir)
    metadata = read_json(package_path / "metadata.json", {})
    platforms = _platforms(metadata.get("platform", ""))
    readiness = connector_readiness(env_file, platforms)
    return {
        "package_dir": str(package_path),
        "run_id": metadata.get("run_id", package_path.name),
        "platforms": platforms,
        "publish_status": metadata.get("publish_status", ""),
        "connector_readiness": readiness,
    }
