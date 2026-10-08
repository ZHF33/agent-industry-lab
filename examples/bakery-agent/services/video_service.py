from __future__ import annotations

from pathlib import Path
from typing import Any

from .common import now_iso, timestamp, write_json


def build_video_task_request(prompt_payload: dict[str, Any], provider: str = "kling") -> dict[str, Any]:
    return {"provider": provider, "prompt": prompt_payload, "async": True, "created_at": now_iso()}


def create_video_task(prompt_payload: dict[str, Any], provider: str = "kling", dry_run: bool = True) -> dict[str, Any]:
    request = build_video_task_request(prompt_payload, provider)
    return {
        "mode": "dry_run" if dry_run else "live_placeholder",
        "provider": provider,
        "task_id": f"video_{timestamp()}",
        "status": "created_placeholder" if dry_run else "created",
        "request_json": request,
        "result_url": "",
        "poll_count": 0,
        "created_at": now_iso(),
    }


def poll_video_task(task: dict[str, Any]) -> dict[str, Any]:
    updated = dict(task)
    updated["poll_count"] = int(updated.get("poll_count", 0)) + 1
    updated["status"] = "completed_placeholder"
    updated["updated_at"] = now_iso()
    return updated


def save_video_result(result: dict[str, Any], out_dir: str | Path = "runs/generated_videos") -> Path:
    path = Path(out_dir)
    if not path.is_absolute():
        from .common import ROOT

        path = ROOT / path
    path.mkdir(parents=True, exist_ok=True)
    return write_json(path / f"{result.get('task_id', 'video')}.json", result)
