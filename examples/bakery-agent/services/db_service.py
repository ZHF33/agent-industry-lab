from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from .common import ROOT, now_iso, resolve_path

DEFAULT_DB = ROOT / "data" / "agent_ops.sqlite3"

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS campaigns (
    campaign_id TEXT PRIMARY KEY,
    campaign_name TEXT NOT NULL,
    campaign_type TEXT,
    product_name TEXT,
    platform TEXT,
    objective TEXT,
    status TEXT NOT NULL,
    start_date TEXT,
    end_date TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS content_runs (
    run_id TEXT PRIMARY KEY,
    campaign_id TEXT,
    product_name TEXT,
    platform TEXT,
    content_goal TEXT,
    dify_status TEXT,
    approval_status TEXT,
    package_path TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    raw_output_json TEXT,
    FOREIGN KEY(campaign_id) REFERENCES campaigns(campaign_id)
);

CREATE TABLE IF NOT EXISTS generated_assets (
    asset_id TEXT PRIMARY KEY,
    run_id TEXT,
    task_id TEXT,
    asset_type TEXT NOT NULL,
    provider TEXT,
    prompt TEXT,
    status TEXT NOT NULL,
    local_path TEXT,
    remote_url TEXT,
    request_json TEXT,
    response_json TEXT,
    error_message TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(run_id) REFERENCES content_runs(run_id)
);

CREATE TABLE IF NOT EXISTS approval_reviews (
    review_id TEXT PRIMARY KEY,
    run_id TEXT,
    package_path TEXT,
    status TEXT NOT NULL,
    reviewer_note TEXT,
    risk_level TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(run_id) REFERENCES content_runs(run_id)
);

CREATE TABLE IF NOT EXISTS tasks (
    task_id TEXT PRIMARY KEY,
    task_type TEXT NOT NULL,
    status TEXT NOT NULL,
    provider TEXT,
    related_run_id TEXT,
    related_package_path TEXT,
    related_asset_id TEXT,
    input_json TEXT,
    output_json TEXT,
    error_message TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS campaign_history (
    history_id TEXT PRIMARY KEY,
    campaign_id TEXT,
    run_id TEXT,
    platform TEXT,
    published_at TEXT,
    impressions INTEGER,
    likes INTEGER,
    saves INTEGER,
    comments INTEGER,
    conversion_notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(campaign_id) REFERENCES campaigns(campaign_id),
    FOREIGN KEY(run_id) REFERENCES content_runs(run_id)
);
"""


def make_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def init_db(db_path: str | Path = DEFAULT_DB) -> Path:
    path = resolve_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        migrate_legacy_tables(conn)
        conn.executescript(SCHEMA)
    return path


def table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    try:
        return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    except sqlite3.DatabaseError:
        return set()


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name = ?", (table,)).fetchone()
    return bool(row)


def migrate_legacy_tables(conn: sqlite3.Connection) -> None:
    legacy_specs = {
        "content_runs": "run_id",
        "generated_assets": "asset_id",
        "approval_reviews": "review_id",
        "campaign_history": "history_id",
    }
    for table, required_column in legacy_specs.items():
        if table_exists(conn, table) and required_column not in table_columns(conn, table):
            suffix = now_iso().replace("-", "").replace(":", "").replace("T", "_")
            conn.execute(f"ALTER TABLE {table} RENAME TO {table}_legacy_{suffix}")


def get_connection(db_path: str | Path = DEFAULT_DB) -> sqlite3.Connection:
    path = init_db(db_path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def dumps(data: Any) -> str:
    if isinstance(data, str):
        return data
    return json.dumps(data if data is not None else {}, ensure_ascii=False)


def upsert_campaign(conn: sqlite3.Connection, campaign: dict[str, Any]) -> str:
    campaign_id = campaign.get("campaign_id") or make_id("campaign")
    now = now_iso()
    conn.execute(
        """
        INSERT INTO campaigns(campaign_id, campaign_name, campaign_type, product_name, platform, objective, status, start_date, end_date, notes, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(campaign_id) DO UPDATE SET
            campaign_name=excluded.campaign_name, campaign_type=excluded.campaign_type, product_name=excluded.product_name,
            platform=excluded.platform, objective=excluded.objective, status=excluded.status, start_date=excluded.start_date,
            end_date=excluded.end_date, notes=excluded.notes, updated_at=excluded.updated_at
        """,
        (
            campaign_id,
            campaign.get("campaign_name", campaign_id),
            campaign.get("campaign_type", ""),
            campaign.get("product_name", ""),
            campaign.get("platform", ""),
            campaign.get("objective", ""),
            campaign.get("status", "active"),
            campaign.get("start_date", ""),
            campaign.get("end_date", ""),
            campaign.get("notes", ""),
            campaign.get("created_at", now),
            campaign.get("updated_at", now),
        ),
    )
    return campaign_id


def upsert_content_run(conn: sqlite3.Connection, run: dict[str, Any]) -> str:
    run_id = run.get("run_id") or make_id("run")
    now = now_iso()
    conn.execute(
        """
        INSERT INTO content_runs(run_id, campaign_id, product_name, platform, content_goal, dify_status, approval_status, package_path, created_at, updated_at, raw_output_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(run_id) DO UPDATE SET
            campaign_id=excluded.campaign_id, product_name=excluded.product_name, platform=excluded.platform,
            content_goal=excluded.content_goal, dify_status=excluded.dify_status, approval_status=excluded.approval_status,
            package_path=excluded.package_path, updated_at=excluded.updated_at, raw_output_json=excluded.raw_output_json
        """,
        (
            run_id,
            run.get("campaign_id") or None,
            run.get("product_name", ""),
            run.get("platform", ""),
            run.get("content_goal", ""),
            run.get("dify_status", ""),
            run.get("approval_status", run.get("status", "pending")),
            run.get("package_path", ""),
            run.get("created_at", now),
            run.get("updated_at", now),
            dumps(run.get("raw_output_json", {})),
        ),
    )
    return run_id


def upsert_asset(conn: sqlite3.Connection, asset: dict[str, Any]) -> str:
    asset_id = asset.get("asset_id") or make_id("asset")
    now = now_iso()
    conn.execute(
        """
        INSERT INTO generated_assets(asset_id, run_id, task_id, asset_type, provider, prompt, status, local_path, remote_url, request_json, response_json, error_message, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(asset_id) DO UPDATE SET
            run_id=excluded.run_id, task_id=excluded.task_id, asset_type=excluded.asset_type, provider=excluded.provider,
            prompt=excluded.prompt, status=excluded.status, local_path=excluded.local_path, remote_url=excluded.remote_url,
            request_json=excluded.request_json, response_json=excluded.response_json, error_message=excluded.error_message,
            updated_at=excluded.updated_at
        """,
        (
            asset_id,
            asset.get("run_id", ""),
            asset.get("task_id", ""),
            asset.get("asset_type", ""),
            asset.get("provider", ""),
            asset.get("prompt", ""),
            asset.get("status", "pending"),
            asset.get("local_path", ""),
            asset.get("remote_url", ""),
            dumps(asset.get("request_json", {})),
            dumps(asset.get("response_json", {})),
            asset.get("error_message", ""),
            asset.get("created_at", now),
            asset.get("updated_at", now),
        ),
    )
    return asset_id


def upsert_approval_review(conn: sqlite3.Connection, review: dict[str, Any]) -> str:
    review_id = review.get("review_id") or make_id("review")
    now = now_iso()
    conn.execute(
        """
        INSERT INTO approval_reviews(review_id, run_id, package_path, status, reviewer_note, risk_level, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(review_id) DO UPDATE SET
            run_id=excluded.run_id, package_path=excluded.package_path, status=excluded.status,
            reviewer_note=excluded.reviewer_note, risk_level=excluded.risk_level, updated_at=excluded.updated_at
        """,
        (
            review_id,
            review.get("run_id", ""),
            review.get("package_path", ""),
            review.get("status", ""),
            review.get("reviewer_note", review.get("note", "")),
            review.get("risk_level", ""),
            review.get("created_at", now),
            review.get("updated_at", now),
        ),
    )
    return review_id


def upsert_task(conn: sqlite3.Connection, task: dict[str, Any]) -> str:
    task_id = task.get("task_id") or make_id("task")
    now = now_iso()
    conn.execute(
        """
        INSERT INTO tasks(task_id, task_type, status, provider, related_run_id, related_package_path, related_asset_id, input_json, output_json, error_message, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(task_id) DO UPDATE SET
            task_type=excluded.task_type, status=excluded.status, provider=excluded.provider,
            related_run_id=excluded.related_run_id, related_package_path=excluded.related_package_path,
            related_asset_id=excluded.related_asset_id, input_json=excluded.input_json, output_json=excluded.output_json,
            error_message=excluded.error_message, updated_at=excluded.updated_at
        """,
        (
            task_id,
            task.get("task_type", ""),
            task.get("status", "pending"),
            task.get("provider", ""),
            task.get("related_run_id", ""),
            task.get("related_package_path", ""),
            task.get("related_asset_id", ""),
            dumps(task.get("input_json", {})),
            dumps(task.get("output_json", {})),
            task.get("error_message", ""),
            task.get("created_at", now),
            task.get("updated_at", now),
        ),
    )
    return task_id


def upsert_campaign_history(conn: sqlite3.Connection, history: dict[str, Any]) -> str:
    history_id = history.get("history_id") or make_id("history")
    now = now_iso()
    conn.execute(
        """
        INSERT INTO campaign_history(history_id, campaign_id, run_id, platform, published_at, impressions, likes, saves, comments, conversion_notes, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(history_id) DO UPDATE SET
            campaign_id=excluded.campaign_id, run_id=excluded.run_id, platform=excluded.platform,
            published_at=excluded.published_at, impressions=excluded.impressions, likes=excluded.likes,
            saves=excluded.saves, comments=excluded.comments, conversion_notes=excluded.conversion_notes,
            updated_at=excluded.updated_at
        """,
        (
            history_id,
            history.get("campaign_id", ""),
            history.get("run_id", ""),
            history.get("platform", ""),
            history.get("published_at", ""),
            int(history.get("impressions") or 0),
            int(history.get("likes") or 0),
            int(history.get("saves") or 0),
            int(history.get("comments") or 0),
            history.get("conversion_notes", ""),
            history.get("created_at", now),
            history.get("updated_at", now),
        ),
    )
    return history_id


def query_recent_runs(conn: sqlite3.Connection, limit: int = 10) -> list[dict[str, Any]]:
    rows = conn.execute("SELECT * FROM content_runs ORDER BY updated_at DESC LIMIT ?", (limit,)).fetchall()
    return [dict(row) for row in rows]
