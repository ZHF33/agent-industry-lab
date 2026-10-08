from __future__ import annotations

from pathlib import Path
from typing import Any

from . import approval_service, db_service, db_sync_service, image_service
from .common import now_iso, read_json, resolve_path, timestamp, write_json


def load_metadata(package_dir: str | Path) -> dict[str, Any]:
    package_path = resolve_path(package_dir)
    metadata = read_json(package_path / "metadata.json", {})
    if not metadata:
        raise RuntimeError(f"Approval package metadata not found: {package_path}")
    return metadata


def find_package_by_run_id(run_id: str, queue: str | Path = "runs/approval_queue") -> Path:
    queue_path = resolve_path(queue)
    package = queue_path / run_id
    if package.exists():
        return package
    for candidate in queue_path.glob("run_*") if queue_path.exists() else []:
        metadata = read_json(candidate / "metadata.json", {})
        if metadata.get("run_id") == run_id:
            return candidate
    raise RuntimeError(f"No approval package found for run_id={run_id}")


def latest_approved_package(queue: str | Path = "runs/approval_queue") -> Path:
    queue_path = resolve_path(queue)
    candidates: list[Path] = []
    for package in queue_path.glob("run_*") if queue_path.exists() else []:
        metadata = read_json(package / "metadata.json", {})
        status = metadata.get("approval_status", metadata.get("status", ""))
        if status == "approved":
            candidates.append(package)
    if not candidates:
        raise RuntimeError("No approved approval package found.")
    return max(candidates, key=lambda path: path.stat().st_mtime)


def summarize_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": report.get("status", ""),
        "mode": report.get("mode", ""),
        "metadata_path": report.get("metadata_path", ""),
        "image_paths": report.get("image_paths", []),
        "image_count": len(report.get("images", [])) if isinstance(report.get("images"), list) else len(report.get("image_paths", [])),
        "error_message": report.get("error_message", ""),
    }


def failure_report(package_dir: Path, out_dir: str | Path, *, live: bool, error: Exception) -> dict[str, Any]:
    out = resolve_path(out_dir)
    report = {
        "mode": "live" if live else "dry_run",
        "status": "failed",
        "asset_type": "image_batch",
        "provider": "openai",
        "input": str(package_dir / "enhanced_image_prompt.json"),
        "metadata_path": "",
        "images": [],
        "image_paths": [],
        "error_message": str(error),
        "created_at": now_iso(),
    }
    try:
        out.mkdir(parents=True, exist_ok=True)
        metadata_path = out / f"image_failure_{timestamp()}.json"
        report["metadata_path"] = str(metadata_path)
        write_json(metadata_path, report)
    except Exception:
        # Failure recording must not hide the provider error.
        report["metadata_path"] = ""
    return report


def generate_for_package(
    package_dir: str | Path,
    *,
    out_dir: str | Path,
    live: bool,
    require_key: bool,
    n: int,
    db: str | Path,
    local_demo: bool = False,
    allow_unapproved: bool = False,
    raise_on_failure: bool = True,
) -> dict[str, Any]:
    package_path = resolve_path(package_dir)
    metadata = load_metadata(package_path)
    status = metadata.get("approval_status", metadata.get("status", ""))
    if status != "approved" and not allow_unapproved:
        raise ValueError(f"Image generation requires approved package status, got {status!r}.")
    prompt_path = package_path / "enhanced_image_prompt.json"
    if not read_json(prompt_path, {}):
        raise RuntimeError(f"Enhanced image prompt not found or empty: {prompt_path}")

    error: Exception | None = None
    try:
        report = image_service.generate_openai_image(prompt_path, out_dir, live=live, require_key=require_key, n=n, local_demo=local_demo)
    except Exception as exc:
        error = exc
        report = failure_report(package_path, out_dir, live=live, error=exc)

    approval_service.backfill_asset_result(package_path, "image", report)
    with db_service.get_connection(db) as conn:
        synced = db_sync_service.sync_package(conn, package_path)

    result = {
        "ok": error is None,
        "mode": "local_demo" if local_demo else ("live" if live else "dry_run"),
        "package_dir": str(package_path),
        "run_id": metadata.get("run_id", package_path.name),
        "product_name": metadata.get("product_name", ""),
        "approval_status": status,
        "image_generation": summarize_report(report),
        "db_sync_status": "synced" if synced else "skipped",
        "db": str(resolve_path(db)),
    }
    if error is not None:
        result["error"] = str(error)
        if raise_on_failure:
            raise RuntimeError(str(error))
    return result
