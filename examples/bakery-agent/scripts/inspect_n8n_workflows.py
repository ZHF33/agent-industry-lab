#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_WORKFLOWS = [
    {"id": "v2FullContentPipelineWebhook", "name": "V2 Full Content Pipeline Webhook", "required": True},
    {"id": "v2ContentOperationWebhook", "name": "V2 Content Operation Webhook", "required": True},
    {"id": "v2ApprovalReviewWebhook", "name": "V2 Approval Review Webhook", "required": True},
    {"id": "v2ImageGenerationWebhook", "name": "V2 Image Generation Webhook", "required": True},
    {"id": "v2ImageSelectionWebhook", "name": "V2 Image Selection Webhook", "required": True},
    {"id": "v2PublishDraftWebhook", "name": "V2 Publish Draft Webhook", "required": True},
    {"id": "v2PublishRecordWebhook", "name": "V2 Publish Record Webhook", "required": True},
    {"id": "v2PublishMockWebhook", "name": "V2 Publish Mock Webhook", "required": False},
]

N8N_UI_URL = "http://localhost:5678/home/workflows"


def activation_steps(missing: list[dict[str, Any]], inactive: list[dict[str, Any]]) -> list[dict[str, str]]:
    steps: list[dict[str, str]] = []
    if missing:
        steps.append(
            {
                "action": "open_n8n_workflows",
                "detail": f"Open {N8N_UI_URL}.",
            }
        )
        steps.append(
            {
                "action": "import_missing_workflows",
                "detail": "Import missing workflow JSON files from n8n/workflows/.",
            }
        )
    if inactive:
        if not steps:
            steps.append({"action": "open_n8n_workflows", "detail": f"Open {N8N_UI_URL}."})
        for item in inactive:
            steps.append(
                {
                    "action": "activate_workflow",
                    "detail": f"Open {item['name']} and turn the top-right Active switch on.",
                }
            )
    if missing or inactive:
        steps.append(
            {
                "action": "verify_runtime",
                "detail": "Run: powershell -ExecutionPolicy Bypass -File scripts\\export_n8n_workflow_state.ps1 -Json",
            }
        )
        steps.append(
            {
                "action": "verify_full_pipeline_manual",
                "detail": "Run after all required workflows are active: .venv\\Scripts\\python.exe scripts\\run_v2_acceptance.py --via-n8n-full --manual-only --json",
            }
        )
        steps.append(
            {
                "action": "verify_full_pipeline_auto_acceptance",
                "detail": "Then run demo acceptance: .venv\\Scripts\\python.exe scripts\\run_v2_acceptance.py --via-n8n-full --json",
            }
        )
    else:
        steps.append({"action": "ready", "detail": "All required V2 workflows are imported and active."})
    return steps


def resolve_db(value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def load_workflows(db: str | Path) -> list[dict[str, Any]]:
    db_path = resolve_db(db)
    if not db_path.exists():
        raise FileNotFoundError(f"n8n database not found: {db_path}")
    with sqlite3.connect(f"{db_path.as_uri()}?mode=ro&immutable=1", uri=True) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT id, name, active FROM workflow_entity ORDER BY name").fetchall()
    return [{"id": row["id"], "name": row["name"], "active": bool(row["active"])} for row in rows]


def inspect(db: str | Path) -> dict[str, Any]:
    workflows = load_workflows(db)
    by_id = {workflow["id"]: workflow for workflow in workflows}
    by_name = {workflow["name"]: workflow for workflow in workflows}
    required_status = []
    missing = []
    inactive = []
    for expected in REQUIRED_WORKFLOWS:
        workflow = by_id.get(expected["id"]) or by_name.get(expected["name"])
        status = {
            **expected,
            "present": bool(workflow),
            "active": bool(workflow and workflow.get("active")),
            "actual_id": workflow.get("id", "") if workflow else "",
        }
        required_status.append(status)
        if expected["required"] and not status["present"]:
            missing.append(expected)
        if expected["required"] and status["present"] and not status["active"]:
            inactive.append(expected)
    return {
        "ok": not missing and not inactive,
        "db": str(resolve_db(db)),
        "required": required_status,
        "missing_required": missing,
        "inactive_required": inactive,
        "workflows": workflows,
        "next_actions": build_next_actions(missing, inactive),
        "activation_steps": activation_steps(missing, inactive),
    }


def build_next_actions(missing: list[dict[str, Any]], inactive: list[dict[str, Any]]) -> list[str]:
    actions: list[str] = []
    if missing:
        actions.append("Import missing workflow JSON files from n8n/workflows/ in the n8n UI.")
    if inactive:
        names = ", ".join(item["name"] for item in inactive)
        actions.append(f"Open n8n UI and turn Active on for: {names}.")
    if not actions:
        actions.append("All required V2 workflows are imported and active.")
    return actions


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect an exported n8n SQLite database for required Bakery V2 workflows.")
    parser.add_argument("--db", default="runs/n8n_database_inspect.sqlite")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = inspect(args.db)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"ok: {result['ok']}")
        for item in result["required"]:
            state = "active" if item["active"] else "inactive" if item["present"] else "missing"
            required = "required" if item["required"] else "optional"
            print(f"- {state}: {item['name']} ({required})")
        for action in result["next_actions"]:
            print(f"next: {action}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
