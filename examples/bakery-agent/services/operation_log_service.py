from __future__ import annotations

from pathlib import Path
from typing import Any

from .common import ROOT, now_iso, read_json, resolve_path, write_json

DEFAULT_LOG = ROOT / "runs" / "operation_log.jsonl"


def append_event(event_type: str, payload: dict[str, Any], log_path: str | Path = DEFAULT_LOG) -> dict[str, Any]:
    path = resolve_path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "created_at": now_iso(),
        "event_type": event_type,
        "payload": payload,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(__import__("json").dumps(event, ensure_ascii=False) + "\n")
    return event


def write_run_archive(run_id: str, summary: dict[str, Any], out_dir: str | Path = "runs/operation_archive") -> Path:
    path = resolve_path(out_dir)
    path.mkdir(parents=True, exist_ok=True)
    archive_path = path / f"{run_id}.json"
    write_json(archive_path, {"archived_at": now_iso(), **summary})
    return archive_path


def load_recent_events(limit: int = 20, log_path: str | Path = DEFAULT_LOG) -> list[dict[str, Any]]:
    path = resolve_path(log_path)
    if not path.exists():
        return []
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    events: list[dict[str, Any]] = []
    for line in lines[-limit:]:
        events.append(read_json_text(line))
    return events


def read_json_text(text: str) -> dict[str, Any]:
    import json

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"created_at": "", "event_type": "corrupt_log_line", "payload": {"line": text}}
