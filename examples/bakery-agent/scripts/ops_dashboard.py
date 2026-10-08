#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import list_approval_queue
from services import db_service, image_service
from services.common import ROOT, load_dotenv, resolve_path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

CONTENT_OPERATION_WEBHOOK = "http://localhost:5678/webhook/v2ContentOperationWebhook/contentrequestwebhook/bakery-content-request"
APPROVAL_REVIEW_WEBHOOK = "http://localhost:5678/webhook/v2ApprovalReviewWebhook/approvalreviewwebhook/bakery-approval-review"
IMAGE_GENERATION_WEBHOOK = "http://localhost:5678/webhook/v2ImageGenerationWebhook/imagegenerationwebhook/bakery-image-generate"
IMAGE_SELECTION_WEBHOOK = "http://localhost:5678/webhook/v2ImageSelectionWebhook/imageselectionwebhook/bakery-image-select"
PUBLISH_DRAFT_WEBHOOK = "http://localhost:5678/webhook/v2PublishDraftWebhook/publishdraftwebhook/bakery-publish-draft"
PUBLISH_RECORD_WEBHOOK = "http://localhost:5678/webhook/v2PublishRecordWebhook/publishrecordwebhook/bakery-publish-record"
PUBLISH_MOCK_WEBHOOK = "http://localhost:5678/webhook/v2PublishMockWebhook/publishmockwebhook/bakery-publish-mock"
FULL_PIPELINE_WEBHOOK = "http://localhost:5678/webhook/v2FullContentPipelineWebhook/fullpipelinewebhook/bakery-full-pipeline"
IMAGE_COMPLETE_STATUSES = {"completed", "succeeded", "generated", "prepared"}


def fetch_rows(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    return [dict(row) for row in conn.execute(sql, params).fetchall()]


def display_path(value: str) -> str:
    if not value:
        return ""
    if value.startswith("/workspace/"):
        value = value.removeprefix("/workspace/")
    path = Path(value)
    if not path.is_absolute():
        return str(path).replace("\\", "/")
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def load_queue(queue: str | Path, limit: int) -> list[dict[str, Any]]:
    queue_path = Path(queue)
    if not queue_path.is_absolute():
        queue_path = ROOT / queue_path
    packages = sorted([p for p in queue_path.glob("run_*") if p.is_dir()], key=lambda p: p.stat().st_mtime, reverse=True) if queue_path.exists() else []
    rows = [list_approval_queue.load_package_summary(path) for path in packages[:limit]]
    for row in rows:
        row["package_dir"] = display_path(str(row.get("package_dir", "")))
    return rows


def readiness(env_path: str | Path = ".env") -> dict[str, Any]:
    env = load_dotenv(env_path)
    image_readiness = image_service.live_image_readiness(require_agent_api_allow=True)
    return {
        "dify_live_ready": bool(env.get("DIFY_BASE_URL") and env.get("DIFY_API_KEY")),
        "openai_image_ready": bool(env.get("OPENAI_API_KEY")),
        "agent_api_token_configured": bool(env.get("AGENT_API_TOKEN")),
        "agent_api_live_image_allowed": env.get("AGENT_API_ALLOW_LIVE_IMAGE", "").lower() in {"1", "true", "yes"},
        "live_image_ready": image_readiness["ready"],
        "live_image_blockers": image_readiness["blockers"],
        "image_provider": image_readiness["provider"],
        "image_model": image_readiness["model"],
        "image_size": image_readiness["size"],
        "image_quality": image_readiness["quality"],
    }


def next_action_for(item: dict[str, Any]) -> dict[str, Any]:
    status = item.get("status", "")
    package = item.get("package_dir", "")
    base = {
        "run_id": item.get("run_id", ""),
        "status": status,
        "product_name": item.get("product_name", ""),
        "package": package,
    }
    if status == "pending":
        return {
            **base,
            "action": "human_review",
            "description": "Review content and image prompts, then approve, reject, or request revision.",
            "webhook": APPROVAL_REVIEW_WEBHOOK,
            "suggested_payload": {"package": package, "status": "approved", "note": "Approved after human review.", "create_revision": False},
        }
    if status == "needs_revision":
        return {
            **base,
            "action": "create_revision",
            "description": "Send revision feedback and create a revision request through n8n.",
            "webhook": APPROVAL_REVIEW_WEBHOOK,
            "suggested_payload": {"package": package, "status": "needs_revision", "note": "Describe required edits.", "create_revision": True},
        }
    if status == "pending_revision_review":
        return {
            **base,
            "action": "review_revision",
            "description": "Review the prepared revision request or live revision output, then approve or request another revision.",
            "webhook": APPROVAL_REVIEW_WEBHOOK,
            "suggested_payload": {"package": package, "status": "approved", "note": "Revision approved after review.", "create_revision": False},
        }
    if status == "approved" and item.get("image_status", "") not in IMAGE_COMPLETE_STATUSES:
        return {
            **base,
            "action": "generate_images",
            "description": "Generate or prepare image assets for the approved package through n8n.",
            "webhook": IMAGE_GENERATION_WEBHOOK,
            "suggested_payload": {"package": package, "live": False, "out_dir": "runs/generated_images"},
        }
    if status == "approved" and item.get("image_status", "") in IMAGE_COMPLETE_STATUSES and not item.get("image_has_files"):
        return {
            **base,
            "action": "generate_local_demo_images",
            "description": "Generate local demo PNG image files for visible review without a paid image provider.",
            "webhook": IMAGE_GENERATION_WEBHOOK,
            "suggested_payload": {"package": package, "local_demo": True, "n": 1, "out_dir": "runs/generated_images"},
        }
    if status == "approved" and item.get("image_status", "") in IMAGE_COMPLETE_STATUSES and item.get("image_has_files") and not item.get("selected_image_id"):
        image_ids = item.get("image_ids", [])
        suggested_image = image_ids[0] if image_ids else ""
        return {
            **base,
            "action": "select_image",
            "description": "Select the final image variant before preparing a publish draft.",
            "webhook": IMAGE_SELECTION_WEBHOOK,
            "suggested_payload": {"package": package, "image_id": suggested_image, "note": "Selected after human review."},
        }
    publish_status = item.get("publish_status", "")
    if status == "approved" and item.get("selected_image_id") and publish_status not in {"draft_prepared", "partially_published", "published"}:
        return {
            **base,
            "action": "prepare_publish_draft",
            "description": "Prepare a manual publish draft after final image selection.",
            "webhook": PUBLISH_DRAFT_WEBHOOK,
            "suggested_payload": {"package": package},
        }
    pending_platforms = item.get("pending_publish_platforms", [])
    if status == "approved" and publish_status in {"draft_prepared", "partially_published", "published"} and pending_platforms:
        platform = pending_platforms[0]
        return {
            **base,
            "action": "record_manual_publish",
            "description": f"Record the manual {platform} publish result after posting outside the system.",
            "webhook": PUBLISH_RECORD_WEBHOOK,
            "suggested_payload": {"package": package, "platform": platform, "published_url": "", "note": "Manual publish recorded."},
        }
    return {**base, "action": "none", "description": "No immediate operator action required."}


def build_dashboard(db: str | Path, queue: str | Path, limit: int) -> dict[str, Any]:
    db_path = db_service.init_db(db)
    queue_rows = load_queue(queue, limit)
    status_counts = Counter(row.get("status", "") or "unknown" for row in queue_rows)
    paired_actions = [(row, next_action_for(row)) for row in queue_rows]
    actionable_pairs = [(row, action) for row, action in paired_actions if action.get("action") != "none"]
    action_items = [row for row, _action in actionable_pairs]
    next_actions = [action for _row, action in actionable_pairs[:limit]]

    with db_service.get_connection(db_path) as conn:
        recent_runs = fetch_rows(
            conn,
            """
            SELECT run_id, product_name, platform, approval_status, updated_at, package_path
            FROM content_runs
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        task_counts = fetch_rows(conn, "SELECT status, COUNT(*) AS count FROM tasks GROUP BY status ORDER BY status")
        asset_counts = fetch_rows(conn, "SELECT status, COUNT(*) AS count FROM generated_assets GROUP BY status ORDER BY status")
    for run in recent_runs:
        run["package_path"] = display_path(str(run.get("package_path", "")))

    return {
        "db": str(resolve_path(db_path)),
        "approval_queue": str(resolve_path(queue)),
        "readiness": readiness(),
        "queue_status_counts": dict(sorted(status_counts.items())),
        "action_item_count": len(action_items),
        "action_items": action_items[:limit],
        "next_actions": next_actions,
        "recent_runs": recent_runs,
        "task_counts": task_counts,
        "asset_counts": asset_counts,
    }


def print_text(report: dict[str, Any]) -> None:
    print("Bakery AI Ops Dashboard")
    print(f"DB: {report['db']}")
    print(f"Approval queue: {report['approval_queue']}")
    print("")
    print("Readiness:")
    for key, value in report["readiness"].items():
        print(f"- {key}: {value}")
    print("")
    print("Queue status counts:")
    for status, count in report["queue_status_counts"].items():
        print(f"- {status}: {count}")
    print("")
    print(f"Action items: {report['action_item_count']}")
    for item in report["action_items"]:
        print(f"- {item['status']}: {item['product_name']} ({item['run_id']}) {item['package_dir']}")
    print("")
    print("Next actions:")
    for action in report["next_actions"]:
        print(f"- {action['action']}: {action['product_name']} ({action['run_id']})")


def main() -> int:
    parser = argparse.ArgumentParser(description="Show a daily operations dashboard for the Bakery AI Agent.")
    parser.add_argument("--db", default=str(db_service.DEFAULT_DB.relative_to(ROOT)))
    parser.add_argument("--queue", default="runs/approval_queue")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = build_dashboard(args.db, args.queue, args.limit)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_text(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
