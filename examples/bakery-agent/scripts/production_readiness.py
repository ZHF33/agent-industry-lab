#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import check_system_health, inspect_n8n_workflows
from services import image_service, publisher_service
from services.common import ROOT, load_dotenv, read_json, resolve_path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


WEBHOOK_FILES = [
    "n8n/workflows/v2_full_content_pipeline_webhook.json",
    "n8n/workflows/v2_content_operation_webhook.json",
    "n8n/workflows/v2_approval_review_webhook.json",
    "n8n/workflows/v2_image_generation_webhook.json",
    "n8n/workflows/v2_image_selection_webhook.json",
    "n8n/workflows/v2_publish_draft_webhook.json",
    "n8n/workflows/v2_publish_record_webhook.json",
    "n8n/workflows/v2_publish_mock_webhook.json",
]


def _platforms(value: str) -> list[str]:
    return [item.strip() for item in str(value or "").split(",") if item.strip()] or ["xiaohongshu"]


def _path_exists(value: str) -> bool:
    if not value:
        return False
    return resolve_path(value).exists()


def _latest_complete_run(queue: str | Path = "runs/approval_queue") -> dict[str, Any]:
    queue_path = resolve_path(queue)
    candidates = sorted([path for path in queue_path.glob("run_*") if path.is_dir()], key=lambda path: path.stat().st_mtime, reverse=True) if queue_path.exists() else []
    for package in candidates:
        metadata = read_json(package / "metadata.json", {})
        if not isinstance(metadata, dict):
            continue
        platforms = _platforms(metadata.get("platform", ""))
        records = metadata.get("publish_records", [])
        record_platforms = [str(record.get("platform", "")) for record in records if isinstance(record, dict)]
        selected = metadata.get("assets", {}).get("image_generation", {}).get("selected_image", {}) if isinstance(metadata.get("assets"), dict) else {}
        selected_paths = selected.get("image_paths", []) if isinstance(selected, dict) else []
        complete = (
            metadata.get("approval_status", metadata.get("status", "")) == "approved"
            and metadata.get("image_status", "") in {"completed", "generated", "prepared"}
            and bool(metadata.get("selected_image_id") or metadata.get("assets", {}).get("image_generation", {}).get("selected_image_id"))
            and metadata.get("publish_status") == "published"
            and all(platform in record_platforms for platform in platforms)
            and any(_path_exists(path) for path in selected_paths)
        )
        if complete:
            return {
                "found": True,
                "run_id": metadata.get("run_id", package.name),
                "package_dir": str(package),
                "product_name": metadata.get("product_name", ""),
                "platforms": platforms,
                "selected_image_id": metadata.get("selected_image_id", ""),
                "publish_record_count": len(records) if isinstance(records, list) else 0,
            }
    return {"found": False}


def _workflow_readiness() -> dict[str, Any]:
    missing = [rel for rel in WEBHOOK_FILES if not (ROOT / rel).exists()]
    inactive = []
    wrong_nodes = []
    for rel in WEBHOOK_FILES:
        path = ROOT / rel
        if not path.exists():
            continue
        workflow = json.loads(path.read_text(encoding="utf-8"))
        node_types = {node.get("type", "") for node in workflow.get("nodes", [])}
        if workflow.get("active") is not True:
            inactive.append(rel)
        if "n8n-nodes-base.webhook" not in node_types or "n8n-nodes-base.httpRequest" not in node_types:
            wrong_nodes.append(rel)
    blockers = []
    if missing:
        blockers.append(f"Missing workflow files: {', '.join(missing)}")
    # Public templates are inactive; runtime activation is checked from n8n DB.
    if wrong_nodes:
        blockers.append(f"Workflow definitions missing webhook/httpRequest nodes: {', '.join(wrong_nodes)}")
    return {"ok": not blockers, "blockers": blockers, "files": WEBHOOK_FILES}


def build_report(env_file: str | Path = ".env", queue: str | Path = "runs/approval_queue", n8n_db: str | Path = "") -> dict[str, Any]:
    env = load_dotenv(env_file)
    latest_complete = _latest_complete_run(queue)
    workflow = _workflow_readiness()
    db_issues = check_system_health.check_runtime_db()
    image_readiness = image_service.live_image_readiness(require_agent_api_allow=True)
    base_env_missing = [key for key in ["AGENT_API_TOKEN", "N8N_WEBHOOK_SECRET", "N8N_BASE_URL", "AGENT_API_URL"] if not env.get(key)]

    local_demo_blockers = []
    if not latest_complete.get("found"):
        local_demo_blockers.append("No complete approval package found with selected image files and all platform publish records.")
    if db_issues:
        local_demo_blockers.append("Runtime SQLite consistency issues exist.")

    n8n_blockers = []
    if base_env_missing:
        n8n_blockers.append(f"Missing local automation env keys: {', '.join(base_env_missing)}")
    n8n_blockers.extend(workflow["blockers"])
    n8n_runtime: dict[str, Any] = {"checked": False}
    if n8n_db:
        try:
            n8n_runtime = inspect_n8n_workflows.inspect(n8n_db)
            n8n_runtime["checked"] = True
            for item in n8n_runtime.get("missing_required", []):
                n8n_blockers.append(f"n8n runtime missing required workflow: {item['name']}")
            for item in n8n_runtime.get("inactive_required", []):
                n8n_blockers.append(f"n8n runtime required workflow is inactive: {item['name']}")
        except Exception as exc:
            n8n_runtime = {"checked": True, "ok": False, "error": str(exc)}
            n8n_blockers.append(f"n8n runtime workflow inspection failed: {exc}")
    else:
        n8n_blockers.append(
            "n8n runtime workflow state has not been checked. Export n8n state with "
            "scripts/export_n8n_workflow_state.ps1 and pass --n8n-db runs/n8n_database_inspect.sqlite."
        )

    publish_readiness = publisher_service.connector_readiness(env_file, ["xiaohongshu", "douyin"])

    stages = {
        "local_demo_chain": {
            "ok": not local_demo_blockers,
            "blockers": local_demo_blockers,
            "evidence": latest_complete,
        },
        "n8n_orchestration": {
            "ok": not n8n_blockers,
            "blockers": n8n_blockers,
            "evidence": {
                "workflow_files": workflow["files"],
                "env_keys_present": {key: bool(env.get(key)) for key in ["AGENT_API_TOKEN", "N8N_WEBHOOK_SECRET", "N8N_BASE_URL", "AGENT_API_URL"]},
                "runtime": n8n_runtime,
            },
        },
        "live_image_generation": {
            "ok": bool(image_readiness["ready"]),
            "blockers": image_readiness["blockers"],
            "evidence": image_readiness,
        },
        "external_auto_publish": {
            "ok": bool(publish_readiness["live_ready"]),
            "blockers": publish_readiness["blockers"],
            "evidence": publish_readiness,
        },
    }
    production_ready = all(stage["ok"] for stage in stages.values())
    return {
        "ok": production_ready,
        "production_ready": production_ready,
        "summary": "ready" if production_ready else "not_ready",
        "stages": stages,
        "next_unlocks": [
            "Add OPENAI_API_KEY and set AGENT_API_ALLOW_LIVE_IMAGE=true only when paid live image generation is intended.",
            "Add real platform publisher connectors or keep the current manual publish record workflow.",
            "Run powershell -ExecutionPolicy Bypass -File scripts\\export_n8n_workflow_state.ps1 -Json before production readiness checks.",
            "Run python scripts/run_v2_acceptance.py --via-n8n-full --manual-only --json after activating the full pipeline webhook.",
            "Run python scripts/run_v2_acceptance.py --via-n8n-full --json only for demo acceptance that intentionally auto-approves.",
        ],
    }


def print_text(report: dict[str, Any]) -> None:
    print(f"Production readiness: {report['summary']}")
    for name, stage in report["stages"].items():
        status = "ok" if stage["ok"] else "blocked"
        print(f"- {name}: {status}")
        for blocker in stage.get("blockers", []):
            print(f"  - {blocker}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Report production readiness by stage for Bakery AI Agent V2.")
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--queue", default="runs/approval_queue")
    parser.add_argument("--n8n-db", default="", help="Exported n8n SQLite DB for runtime active workflow checks.")
    parser.add_argument("--require-production-ready", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = build_report(args.env_file, args.queue, args.n8n_db)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_text(report)
    return 1 if args.require_production_ready and not report["production_ready"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

