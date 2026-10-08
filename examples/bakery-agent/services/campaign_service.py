from __future__ import annotations

from pathlib import Path
from typing import Any

from . import db_service
from .common import now_iso


def create_campaign(campaign: dict[str, Any], db_path: str | Path = db_service.DEFAULT_DB) -> dict[str, Any]:
    data = {
        "campaign_id": campaign.get("campaign_id") or db_service.make_id("campaign"),
        "campaign_name": campaign.get("campaign_name", "Daily Content Campaign"),
        "campaign_type": campaign.get("campaign_type", "daily_content"),
        "product_name": campaign.get("product_name", "bakery product"),
        "platform": campaign.get("platform", "xiaohongshu,douyin"),
        "objective": campaign.get("objective", "生成待审核内容"),
        "status": campaign.get("status", "active"),
        "start_date": campaign.get("start_date", now_iso()[:10]),
        "end_date": campaign.get("end_date", ""),
        "notes": campaign.get("notes", ""),
        "created_at": campaign.get("created_at", now_iso()),
        "updated_at": now_iso(),
    }
    with db_service.get_connection(db_path) as conn:
        db_service.upsert_campaign(conn, data)
    return data


def attach_content_run_to_campaign(campaign_id: str, run_id: str, db_path: str | Path = db_service.DEFAULT_DB) -> None:
    with db_service.get_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM content_runs WHERE run_id = ?", (run_id,)).fetchone()
        if not row:
            raise RuntimeError(f"Run not found: {run_id}")
        data = dict(row)
        data["campaign_id"] = campaign_id
        data["updated_at"] = now_iso()
        db_service.upsert_content_run(conn, data)


def summarize_campaign(campaign_id: str, db_path: str | Path = db_service.DEFAULT_DB) -> dict[str, Any]:
    with db_service.get_connection(db_path) as conn:
        campaign = conn.execute("SELECT * FROM campaigns WHERE campaign_id = ?", (campaign_id,)).fetchone()
        runs = conn.execute("SELECT count(*) FROM content_runs WHERE campaign_id = ?", (campaign_id,)).fetchone()[0]
        assets = conn.execute(
            "SELECT count(*) FROM generated_assets WHERE run_id IN (SELECT run_id FROM content_runs WHERE campaign_id = ?)",
            (campaign_id,),
        ).fetchone()[0]
    return {"campaign": dict(campaign) if campaign else {}, "run_count": runs, "asset_count": assets}


def update_campaign_status(campaign_id: str, status: str, db_path: str | Path = db_service.DEFAULT_DB) -> dict[str, Any]:
    with db_service.get_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM campaigns WHERE campaign_id = ?", (campaign_id,)).fetchone()
        if not row:
            raise RuntimeError(f"Campaign not found: {campaign_id}")
        data = dict(row)
        data["status"] = status
        data["updated_at"] = now_iso()
        db_service.upsert_campaign(conn, data)
    return summarize_campaign(campaign_id, db_path)["campaign"]
