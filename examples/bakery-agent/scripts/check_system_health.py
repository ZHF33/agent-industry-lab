#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from services import image_service

FULL_PIPELINE_WEBHOOK_PATH = "/webhook/v2FullContentPipelineWebhook/fullpipelinewebhook/bakery-full-pipeline"
FULL_PIPELINE_WEBHOOK_REMEDIATION = [
    "Open n8n at http://localhost:5678/home/workflows.",
    "Import n8n/workflows/v2_full_content_pipeline_webhook.json if the workflow is missing.",
    "Open V2 Full Content Pipeline Webhook.",
    "Turn the workflow Active in the top-right switch.",
    "Run: python scripts/check_system_health.py --live --json.",
]
FULL_PIPELINE_WORKFLOW_FILE = "n8n/workflows/v2_full_content_pipeline_webhook.json"
FULL_PIPELINE_WORKFLOW_NAME = "V2 Full Content Pipeline Webhook"

REQUIRED_ENV_KEYS = [
    "DIFY_BASE_URL",
    "DIFY_API_KEY",
    "N8N_BASE_URL",
    "AGENT_API_URL",
    "AGENT_API_TOKEN",
    "N8N_WEBHOOK_SECRET",
    "N8N_ENCRYPTION_KEY",
]


def load_env(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    if not path.exists():
        return data
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        data[key.strip()] = value.strip()
    return data


def parse_dt(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def path_exists(value: str) -> bool:
    if not value:
        return True
    if value.startswith("/workspace/"):
        return (ROOT / value.removeprefix("/workspace/")).exists()
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path.exists()


def check_runtime_db(max_pending_hours: int = 24) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    db = ROOT / "data" / "agent_ops.sqlite3"
    if not db.exists():
        return [{"severity": "error", "type": "missing_db", "path": str(db)}]
    cutoff = datetime.now() - timedelta(hours=max_pending_hours)
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        for row in conn.execute("SELECT task_id, status, related_package_path, created_at FROM tasks ORDER BY created_at"):
            created = parse_dt(row["created_at"])
            if row["status"] == "pending" and created and created < cutoff:
                issues.append({"severity": "error", "type": "stale_pending_task", "task_id": row["task_id"], "created_at": row["created_at"]})
            if row["related_package_path"] and not path_exists(row["related_package_path"]):
                issues.append({"severity": "error", "type": "missing_task_package", "task_id": row["task_id"], "path": row["related_package_path"]})
        for row in conn.execute("SELECT run_id, package_path FROM content_runs ORDER BY created_at"):
            if row["package_path"] and not path_exists(row["package_path"]):
                issues.append({"severity": "error", "type": "missing_content_run_package", "run_id": row["run_id"], "path": row["package_path"]})
    finally:
        conn.close()
    return issues


def http_json(url: str, timeout: int = 5) -> tuple[bool, Any]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            try:
                return True, json.loads(body)
            except json.JSONDecodeError:
                return True, body[:500]
    except (urllib.error.URLError, TimeoutError) as exc:
        return False, str(exc)


def http_post_json(url: str, payload: dict[str, Any], headers: dict[str, str] | None = None, timeout: int = 5) -> tuple[int, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8", **(headers or {})},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            return response.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(body)
        except json.JSONDecodeError:
            detail = body[:500]
        return exc.code, detail
    except (urllib.error.URLError, TimeoutError) as exc:
        return 0, str(exc)


def host_reachable_url(url: str) -> str:
    return (
        url.replace("http://host.docker.internal", "http://127.0.0.1")
        .replace("https://host.docker.internal", "https://127.0.0.1")
        .replace("http://agent-api", "http://127.0.0.1")
        .replace("https://agent-api", "https://127.0.0.1")
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Bakery AI Agent V2 system health.")
    parser.add_argument("--live", action="store_true", help="Also check live local HTTP endpoints.")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--max-pending-hours", type=int, default=24)
    args = parser.parse_args()

    env_example = load_env(ROOT / ".env.example")
    env = load_env(ROOT / ".env")
    checks: list[dict[str, Any]] = []

    missing_example = [key for key in REQUIRED_ENV_KEYS if key not in env_example]
    checks.append({"name": "env_example_required_keys", "ok": not missing_example, "missing": missing_example})

    missing_local = [key for key in REQUIRED_ENV_KEYS if key not in env]
    checks.append({"name": "env_required_keys", "ok": not missing_local, "missing": missing_local})
    checks.append({"name": "agent_api_token_configured", "ok": bool(env.get("AGENT_API_TOKEN")), "configured": bool(env.get("AGENT_API_TOKEN"))})
    checks.append({"name": "image_live_readiness", "ok": True, "readiness": image_service.live_image_readiness(require_agent_api_allow=True)})

    workflow_path = ROOT / "n8n" / "workflows" / "v2_content_operation_webhook.json"
    workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
    node_types = {node["type"] for node in workflow["nodes"]}
    node_names = {node["name"] for node in workflow["nodes"]}
    workflow_ok = (
        workflow.get("active") is True
        and "n8n-nodes-base.webhook" in node_types
        and "n8n-nodes-base.httpRequest" in node_types
        and "n8n-nodes-base.executeCommand" not in node_types
        and "Daily Trigger" not in node_names
    )
    checks.append({"name": "production_webhook_workflow", "ok": workflow_ok, "nodes": sorted(node_names)})

    full_pipeline_workflow_path = ROOT / "n8n" / "workflows" / "v2_full_content_pipeline_webhook.json"
    full_pipeline_workflow = json.loads(full_pipeline_workflow_path.read_text(encoding="utf-8"))
    full_pipeline_node_types = {node["type"] for node in full_pipeline_workflow["nodes"]}
    full_pipeline_node_names = {node["name"] for node in full_pipeline_workflow["nodes"]}
    full_pipeline_workflow_text = json.dumps(full_pipeline_workflow, ensure_ascii=False)
    full_pipeline_workflow_ok = (
        full_pipeline_workflow.get("active") is True
        and "n8n-nodes-base.webhook" in full_pipeline_node_types
        and "n8n-nodes-base.httpRequest" in full_pipeline_node_types
        and "FullPipelineWebhook" in full_pipeline_node_names
        and "Call Full Pipeline API" in full_pipeline_node_names
        and "/pipeline" in full_pipeline_workflow_text
        and "n8n-nodes-base.executeCommand" not in full_pipeline_node_types
    )
    checks.append({"name": "full_pipeline_webhook_workflow", "ok": full_pipeline_workflow_ok, "nodes": sorted(full_pipeline_node_names)})

    approval_workflow_path = ROOT / "n8n" / "workflows" / "v2_approval_review_webhook.json"
    approval_workflow = json.loads(approval_workflow_path.read_text(encoding="utf-8"))
    approval_node_types = {node["type"] for node in approval_workflow["nodes"]}
    approval_node_names = {node["name"] for node in approval_workflow["nodes"]}
    approval_workflow_ok = (
        approval_workflow.get("active") is True
        and "n8n-nodes-base.webhook" in approval_node_types
        and "n8n-nodes-base.httpRequest" in approval_node_types
        and "ApprovalReviewWebhook" in approval_node_names
        and "Call Approval Review API" in approval_node_names
    )
    checks.append({"name": "approval_review_webhook_workflow", "ok": approval_workflow_ok, "nodes": sorted(approval_node_names)})

    image_workflow_path = ROOT / "n8n" / "workflows" / "v2_image_generation_webhook.json"
    image_workflow = json.loads(image_workflow_path.read_text(encoding="utf-8"))
    image_node_types = {node["type"] for node in image_workflow["nodes"]}
    image_node_names = {node["name"] for node in image_workflow["nodes"]}
    image_workflow_text = json.dumps(image_workflow, ensure_ascii=False)
    image_workflow_ok = (
        image_workflow.get("active") is True
        and "n8n-nodes-base.webhook" in image_node_types
        and "n8n-nodes-base.httpRequest" in image_node_types
        and "ImageGenerationWebhook" in image_node_names
        and "Call Image Generation API" in image_node_names
        and "/image/generate" in image_workflow_text
    )
    checks.append({"name": "image_generation_webhook_workflow", "ok": image_workflow_ok, "nodes": sorted(image_node_names)})

    image_selection_workflow_path = ROOT / "n8n" / "workflows" / "v2_image_selection_webhook.json"
    image_selection_workflow = json.loads(image_selection_workflow_path.read_text(encoding="utf-8"))
    image_selection_node_types = {node["type"] for node in image_selection_workflow["nodes"]}
    image_selection_node_names = {node["name"] for node in image_selection_workflow["nodes"]}
    image_selection_workflow_text = json.dumps(image_selection_workflow, ensure_ascii=False)
    image_selection_workflow_ok = (
        image_selection_workflow.get("active") is True
        and "n8n-nodes-base.webhook" in image_selection_node_types
        and "n8n-nodes-base.httpRequest" in image_selection_node_types
        and "ImageSelectionWebhook" in image_selection_node_names
        and "Call Image Selection API" in image_selection_node_names
        and "/image/select" in image_selection_workflow_text
    )
    checks.append({"name": "image_selection_webhook_workflow", "ok": image_selection_workflow_ok, "nodes": sorted(image_selection_node_names)})

    publish_workflow_path = ROOT / "n8n" / "workflows" / "v2_publish_draft_webhook.json"
    publish_workflow = json.loads(publish_workflow_path.read_text(encoding="utf-8"))
    publish_node_types = {node["type"] for node in publish_workflow["nodes"]}
    publish_node_names = {node["name"] for node in publish_workflow["nodes"]}
    publish_workflow_text = json.dumps(publish_workflow, ensure_ascii=False)
    publish_workflow_ok = (
        publish_workflow.get("active") is True
        and "n8n-nodes-base.webhook" in publish_node_types
        and "n8n-nodes-base.httpRequest" in publish_node_types
        and "PublishDraftWebhook" in publish_node_names
        and "Call Publish Draft API" in publish_node_names
        and "/publish/draft" in publish_workflow_text
    )
    checks.append({"name": "publish_draft_webhook_workflow", "ok": publish_workflow_ok, "nodes": sorted(publish_node_names)})

    publish_record_workflow_path = ROOT / "n8n" / "workflows" / "v2_publish_record_webhook.json"
    publish_record_workflow = json.loads(publish_record_workflow_path.read_text(encoding="utf-8"))
    publish_record_node_types = {node["type"] for node in publish_record_workflow["nodes"]}
    publish_record_node_names = {node["name"] for node in publish_record_workflow["nodes"]}
    publish_record_workflow_text = json.dumps(publish_record_workflow, ensure_ascii=False)
    publish_record_workflow_ok = (
        publish_record_workflow.get("active") is True
        and "n8n-nodes-base.webhook" in publish_record_node_types
        and "n8n-nodes-base.httpRequest" in publish_record_node_types
        and "PublishRecordWebhook" in publish_record_node_names
        and "Call Publish Record API" in publish_record_node_names
        and "/publish/record" in publish_record_workflow_text
    )
    checks.append({"name": "publish_record_webhook_workflow", "ok": publish_record_workflow_ok, "nodes": sorted(publish_record_node_names)})

    publish_mock_workflow_path = ROOT / "n8n" / "workflows" / "v2_publish_mock_webhook.json"
    publish_mock_workflow = json.loads(publish_mock_workflow_path.read_text(encoding="utf-8"))
    publish_mock_node_types = {node["type"] for node in publish_mock_workflow["nodes"]}
    publish_mock_node_names = {node["name"] for node in publish_mock_workflow["nodes"]}
    publish_mock_workflow_text = json.dumps(publish_mock_workflow, ensure_ascii=False)
    publish_mock_workflow_ok = (
        publish_mock_workflow.get("active") is True
        and "n8n-nodes-base.webhook" in publish_mock_node_types
        and "n8n-nodes-base.httpRequest" in publish_mock_node_types
        and "PublishMockWebhook" in publish_mock_node_names
        and "Call Publish Mock API" in publish_mock_node_names
        and "/publish/mock" in publish_mock_workflow_text
    )
    checks.append({"name": "publish_mock_webhook_workflow", "ok": publish_mock_workflow_ok, "nodes": sorted(publish_mock_node_names)})

    execute_workflow_path = ROOT / "n8n" / "workflows" / "v2_content_operation_execute_command.json"
    execute_workflow = json.loads(execute_workflow_path.read_text(encoding="utf-8"))
    execute_code = "\n".join(node.get("parameters", {}).get("jsCode", "") for node in execute_workflow["nodes"])
    execute_workflow_ok = execute_workflow.get("active") is False and "image_count must be an integer between 1 and 8" in execute_code
    checks.append({"name": "execute_command_fallback_inactive_and_limited", "ok": execute_workflow_ok, "active": execute_workflow.get("active")})

    db_issues = check_runtime_db(args.max_pending_hours)
    checks.append({"name": "runtime_db", "ok": not db_issues, "issues": db_issues})

    if args.live:
        agent_url = env.get("AGENT_API_URL") or env_example.get("AGENT_API_URL", "http://127.0.0.1:8765")
        health_url = host_reachable_url(agent_url).rstrip("/") + "/health"
        ok, detail = http_json(health_url)
        checks.append({"name": "agent_api_health", "ok": ok, "url": health_url, "configured_url": agent_url, "detail": detail})
        operation_url = host_reachable_url(agent_url).rstrip("/") + "/operation"
        status, detail = http_post_json(operation_url, {"user_request": "health auth probe", "image_count": 1}, timeout=5)
        checks.append({"name": "agent_api_rejects_unauthorized_post", "ok": status == 401, "url": operation_url, "status": status, "detail": detail})
        n8n_url = env.get("N8N_BASE_URL") or env_example.get("N8N_BASE_URL", "http://localhost:5678")
        ok, detail = http_json(n8n_url.rstrip("/") + "/healthz")
        checks.append({"name": "n8n_health", "ok": ok, "url": n8n_url.rstrip("/") + "/healthz", "detail": detail})
        full_pipeline_url = n8n_url.rstrip("/") + FULL_PIPELINE_WEBHOOK_PATH
        status, detail = http_post_json(full_pipeline_url, {"user_request": "health full pipeline protected probe"}, timeout=5)
        protected = status in {400, 401, 403, 500} and "Unauthorized webhook request" in json.dumps(detail, ensure_ascii=False)
        checks.append(
            {
                "name": "n8n_full_pipeline_webhook_reachable_and_protected",
                "ok": protected,
                "url": full_pipeline_url,
                "status": status,
                "detail": detail,
                "workflow_file": FULL_PIPELINE_WORKFLOW_FILE,
                "workflow_name": FULL_PIPELINE_WORKFLOW_NAME,
                "remediation": FULL_PIPELINE_WEBHOOK_REMEDIATION if not protected else [],
            }
        )

    result = {"ok": all(check["ok"] for check in checks), "checks": checks}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for check in checks:
            status = "ok" if check["ok"] else "fail"
            print(f"{status}: {check['name']}")
            if not check["ok"]:
                print(json.dumps(check, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

