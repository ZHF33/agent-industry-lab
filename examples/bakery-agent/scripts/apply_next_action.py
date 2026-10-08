#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import ops_dashboard
from services import approval_service, db_service
from services.common import ROOT, load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def find_action(report: dict[str, Any], *, run_id: str = "", package: str = "") -> dict[str, Any]:
    actions = report.get("next_actions", [])
    if not actions:
        raise RuntimeError("No next actions found in the approval queue.")
    if not run_id and not package:
        if len(actions) == 1:
            return actions[0]
        raise RuntimeError("Multiple next actions found. Pass --run-id or --package.")

    wanted_package = package.replace("\\", "/")
    wanted_package_display = ops_dashboard.display_path(package).replace("\\", "/") if package else ""
    for action in actions:
        action_package = str(action.get("package", "")).replace("\\", "/")
        if run_id and action.get("run_id") == run_id:
            return action
        if wanted_package and (
            action_package == wanted_package
            or action_package == wanted_package_display
            or action_package.endswith(wanted_package)
            or action_package.endswith(wanted_package_display)
        ):
            return action
    raise RuntimeError(f"No next action matched run_id={run_id!r} package={package!r}.")


def build_payload(action: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    payload = dict(action.get("suggested_payload") or {})
    if not payload.get("package"):
        raise RuntimeError("Selected next action does not include a package path.")
    if args.status:
        payload["status"] = args.status
    if args.note:
        payload["note"] = args.note
    if args.create_revision is not None:
        payload["create_revision"] = args.create_revision
    return payload


def webhook_secret(env_path: str | Path = ".env") -> str:
    return load_dotenv(env_path).get("N8N_WEBHOOK_SECRET", "").strip()


def post_json(url: str, payload: dict[str, Any], timeout: int, headers: dict[str, str] | None = None) -> tuple[int, dict[str, Any] | str]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=body, method="POST", headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            text = response.read().decode("utf-8", errors="replace")
            try:
                return response.status, json.loads(text)
            except json.JSONDecodeError:
                return response.status, text
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        try:
            detail: dict[str, Any] | str = json.loads(text)
        except json.JSONDecodeError:
            detail = text
        return exc.code, detail


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply one dashboard next action through the n8n approval webhook.")
    parser.add_argument("--run-id", default="", help="Run ID to act on. Required when multiple next actions exist.")
    parser.add_argument("--package", default="", help="Approval package path to act on.")
    parser.add_argument("--status", default="", choices=[""] + sorted(approval_service.ALLOWED_STATUSES), help="Override approval status.")
    parser.add_argument("--note", default="", help="Override reviewer note.")
    parser.add_argument("--create-revision", dest="create_revision", action="store_true", default=None)
    parser.add_argument("--no-create-revision", dest="create_revision", action="store_false")
    parser.add_argument("--webhook-url", default="", help="Override the selected action webhook URL.")
    parser.add_argument("--db", default=str(db_service.DEFAULT_DB.relative_to(ROOT)))
    parser.add_argument("--queue", default="runs/approval_queue")
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--execute", action="store_true", help="Actually POST to n8n. Without this, only prints the payload.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = ops_dashboard.build_dashboard(args.db, args.queue, args.limit)
    action = find_action(report, run_id=args.run_id, package=args.package)
    payload = build_payload(action, args)
    webhook_url = args.webhook_url or str(action.get("webhook") or ops_dashboard.APPROVAL_REVIEW_WEBHOOK)

    result: dict[str, Any] = {
        "ok": True,
        "mode": "execute" if args.execute else "dry_run",
        "action": {
            "run_id": action.get("run_id", ""),
            "action": action.get("action", ""),
            "status": action.get("status", ""),
            "product_name": action.get("product_name", ""),
            "package": action.get("package", ""),
        },
        "webhook": webhook_url,
        "payload": payload,
        "webhook_secret_configured": bool(webhook_secret(args.env_file)),
    }
    exit_code = 0
    if args.execute:
        secret = webhook_secret(args.env_file)
        if not secret:
            raise RuntimeError("N8N_WEBHOOK_SECRET is required in .env to execute n8n webhook actions.")
        status_code, response = post_json(webhook_url, payload, args.timeout, {"X-Bakery-Webhook-Secret": secret})
        result["http_status"] = status_code
        result["response"] = response
        if status_code >= 400:
            result["ok"] = False
            exit_code = 1

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Mode: {result['mode']}")
        print(f"Action: {result['action']['action']} for {result['action']['product_name']} ({result['action']['run_id']})")
        print(f"Webhook: {result['webhook']}")
        print("Payload:")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        if args.execute:
            print(f"HTTP status: {result['http_status']}")
            print("Response:")
            print(json.dumps(result["response"], ensure_ascii=False, indent=2) if isinstance(result["response"], dict) else result["response"])
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
