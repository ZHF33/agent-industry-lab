from __future__ import annotations

from pathlib import Path
from typing import Any

from . import db_service
from .common import now_iso, read_json, resolve_path, write_json

TASK_STATUSES = {"pending", "running", "succeeded", "failed", "rejected", "needs_revision", "skipped"}
TASK_TYPES = {"content_generation", "image_generation", "video_generation", "approval_review", "revision", "db_sync", "manual_publish_record"}


def create_task(task_type: str, *, provider: str = "", related_run_id: str = "", related_package_path: str = "", related_asset_id: str = "", input_json: dict[str, Any] | None = None, db_path: str | Path = db_service.DEFAULT_DB) -> dict[str, Any]:
    if task_type not in TASK_TYPES:
        raise RuntimeError(f"Invalid task_type: {task_type}")
    task = {
        "task_id": db_service.make_id("task"),
        "task_type": task_type,
        "status": "pending",
        "provider": provider,
        "related_run_id": related_run_id,
        "related_package_path": related_package_path,
        "related_asset_id": related_asset_id,
        "input_json": input_json or {},
        "output_json": {},
        "error_message": "",
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    with db_service.get_connection(db_path) as conn:
        db_service.upsert_task(conn, task)
    return task


def update_task_status(task_id: str, status: str, *, output_json: dict[str, Any] | None = None, error_message: str = "", db_path: str | Path = db_service.DEFAULT_DB) -> dict[str, Any]:
    if status not in TASK_STATUSES:
        raise RuntimeError(f"Invalid task status: {status}")
    with db_service.get_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
        if not row:
            raise RuntimeError(f"Task not found: {task_id}")
        task = dict(row)
        task["status"] = status
        task["output_json"] = output_json or {}
        task["error_message"] = error_message
        task["updated_at"] = now_iso()
        db_service.upsert_task(conn, task)
    return get_task(task_id, db_path)


def get_task(task_id: str, db_path: str | Path = db_service.DEFAULT_DB) -> dict[str, Any]:
    with db_service.get_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
    return dict(row) if row else {}


def list_pending_tasks(db_path: str | Path = db_service.DEFAULT_DB) -> list[dict[str, Any]]:
    with db_service.get_connection(db_path) as conn:
        rows = conn.execute("SELECT * FROM tasks WHERE status = 'pending' ORDER BY created_at").fetchall()
    return [dict(row) for row in rows]


def _update_task_field(task_id: str, field: str, value: str, db_path: str | Path) -> dict[str, Any]:
    with db_service.get_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
        if not row:
            raise RuntimeError(f"Task not found: {task_id}")
        task = dict(row)
        task[field] = value
        task["updated_at"] = now_iso()
        db_service.upsert_task(conn, task)
    return get_task(task_id, db_path)


def link_task_to_approval_package(task_id: str, package_path: str, db_path: str | Path = db_service.DEFAULT_DB) -> dict[str, Any]:
    return _update_task_field(task_id, "related_package_path", package_path, db_path)


def link_task_to_asset(task_id: str, asset_id: str, db_path: str | Path = db_service.DEFAULT_DB) -> dict[str, Any]:
    return _update_task_field(task_id, "related_asset_id", asset_id, db_path)


def append_task_to_package(package_dir: str | Path, task: dict[str, Any]) -> None:
    path = resolve_path(package_dir)
    tasks = read_json(path / "tasks.json", [])
    tasks.append(task)
    write_json(path / "tasks.json", tasks)


def upsert_task_to_package(package_dir: str | Path, task: dict[str, Any]) -> None:
    path = resolve_path(package_dir)
    tasks = read_json(path / "tasks.json", [])
    task_id = task.get("task_id", "")
    replaced = False
    if task_id:
        for index, existing in enumerate(tasks):
            if isinstance(existing, dict) and existing.get("task_id") == task_id:
                tasks[index] = task
                replaced = True
                break
    if not replaced:
        tasks.append(task)
    write_json(path / "tasks.json", tasks)


def upsert_unique_task_to_package(package_dir: str | Path, task: dict[str, Any], unique_fields: list[str]) -> None:
    path = resolve_path(package_dir)
    tasks = read_json(path / "tasks.json", [])
    def same_unique(existing: dict[str, Any]) -> bool:
        return all(existing.get(field) == task.get(field) for field in unique_fields)

    kept = [existing for existing in tasks if not (isinstance(existing, dict) and same_unique(existing))]
    kept.append(task)
    write_json(path / "tasks.json", kept)
