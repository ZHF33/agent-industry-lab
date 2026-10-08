#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import inspect_n8n_workflows, ops_dashboard
from services import approval_service, db_service, db_sync_service, image_generation_service, image_selection_service, publish_service, publisher_service
from services.common import ROOT, load_dotenv, read_json, resolve_path, timestamp

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


N8N_INACTIVE_WEBHOOK_HELP = (
    "n8n production webhook is not registered. The matching workflow is usually inactive. "
    "Open http://localhost:5678/home/workflows, open the V2 workflow, turn Active on, "
    "then run: powershell -ExecutionPolicy Bypass -File scripts\\export_n8n_workflow_state.ps1 -Json"
)


DEFAULT_REQUEST = "今日的爆品是牛肉恰巴塔，生成它的解构风展示图"


def _platforms(value: str) -> list[str]:
    return [item.strip() for item in str(value or "").split(",") if item.strip()] or ["xiaohongshu"]


def _choose_image_id(metadata: dict[str, Any], preferred: str) -> str:
    image_asset = metadata.get("assets", {}).get("image_generation", {})
    images = image_asset.get("images", []) if isinstance(image_asset, dict) else []
    image_ids = [str(image.get("image_id", "")) for image in images if isinstance(image, dict) and image.get("image_id")]
    if not image_ids:
        raise RuntimeError("Acceptance run did not produce image variants.")
    return preferred if preferred in image_ids else image_ids[0]


def _webhook_secret(env_file: str | Path) -> str:
    return load_dotenv(env_file).get("N8N_WEBHOOK_SECRET", "").strip()


def _format_webhook_http_error(url: str, code: int, text: str) -> str:
    try:
        detail: Any = json.loads(text) if text.strip() else {}
    except json.JSONDecodeError:
        detail = text

    detail_text = detail if isinstance(detail, str) else json.dumps(detail, ensure_ascii=False)
    normalized = detail_text.lower()
    if code == 404 and ("not registered" in normalized or "workflow must be active" in normalized):
        return f"Webhook {url} failed with HTTP {code}: {N8N_INACTIVE_WEBHOOK_HELP} Detail: {detail_text}"
    return f"Webhook {url} failed with HTTP {code}: {detail_text}"


def _post_json(url: str, payload: dict[str, Any], timeout: int, headers: dict[str, str]) -> dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=body, method="POST", headers={"Content-Type": "application/json", **headers})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            text = response.read().decode("utf-8", errors="replace")
            data = json.loads(text) if text.strip() else {}
            if response.status >= 400:
                raise RuntimeError(f"Webhook {url} failed with HTTP {response.status}: {data}")
            if not isinstance(data, dict):
                raise RuntimeError(f"Webhook {url} did not return a JSON object.")
            return data
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(_format_webhook_http_error(url, exc.code, text)) from exc


def _preflight_full_pipeline_runtime(n8n_db: str | Path = "") -> dict[str, Any]:
    if not str(n8n_db or "").strip():
        return {"checked": False}
    report = inspect_n8n_workflows.inspect(n8n_db)
    report["checked"] = True
    if not report.get("ok"):
        missing = ", ".join(item["name"] for item in report.get("missing_required", []))
        inactive = ", ".join(item["name"] for item in report.get("inactive_required", []))
        actions = " ".join(report.get("next_actions", []))
        details = []
        if missing:
            details.append(f"missing required workflows: {missing}")
        if inactive:
            details.append(f"inactive required workflows: {inactive}")
        raise RuntimeError(f"n8n runtime preflight failed before calling webhook: {'; '.join(details)}. {actions}")
    return report


def _run_content_operation(args: argparse.Namespace, base_dir: Path, db_path: Path, log_path: Path) -> dict[str, Any]:
    command = [
        sys.executable,
        str(ROOT / "scripts" / "run_content_operation.py"),
        "--mode",
        "dry-run",
        "--request",
        args.request,
        "--image-count",
        str(args.image_count),
        "--platform",
        args.platforms,
        "--campaign-name",
        "V2 Acceptance Content Operation",
        "--db",
        str(db_path),
        "--out-dir",
        str(base_dir / "operations"),
        "--approval-out-dir",
        str(base_dir / "approval_queue"),
        "--image-out-dir",
        str(base_dir / "generated_images"),
        "--archive-out-dir",
        str(base_dir / "operation_archive"),
        "--log",
        str(log_path),
    ]
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"Content operation failed: {completed.stderr[-2000:]}")
    return json.loads(completed.stdout)


def _run_content_operation_via_n8n(args: argparse.Namespace, headers: dict[str, str]) -> dict[str, Any]:
    response = _post_json(
        ops_dashboard.CONTENT_OPERATION_WEBHOOK,
        {
            "user_request": args.request,
            "execution_mode": "dry-run",
            "campaign_name": "V2 n8n Acceptance Content Operation",
            "platforms": args.platforms,
            "image_count": args.image_count,
        },
        args.timeout,
        headers,
    )
    if not response.get("ok"):
        raise RuntimeError(f"n8n content operation failed: {response}")
    operation = response.get("operation", {})
    if not isinstance(operation, dict) or not operation.get("approval_package"):
        raise RuntimeError(f"n8n content operation did not return an approval package: {response}")
    return operation


def _run_full_pipeline_via_n8n(args: argparse.Namespace, headers: dict[str, str]) -> dict[str, Any]:
    manual_only = bool(getattr(args, "manual_only", False))
    payload = {
        "user_request": args.request,
        "execution_mode": "dry-run",
        "platforms": args.platforms,
        "image_count": args.image_count,
        "preferred_image_id": args.preferred_image_id,
        "local_demo": True,
        "mock_publish": bool(args.mock_publish),
        "image_note": args.image_note,
    }
    if manual_only:
        payload["approval_mode"] = "manual"
    else:
        payload.update(
            {
                "auto_approve": True,
                "approval_mode": "auto",
                "approval_note": args.approval_note,
            }
        )
    response = _post_json(
        ops_dashboard.FULL_PIPELINE_WEBHOOK,
        payload,
        args.timeout,
        headers,
    )
    pipeline = response.get("pipeline", {})
    if not response.get("ok") or not isinstance(pipeline, dict) or not pipeline.get("ok"):
        raise RuntimeError(f"n8n full pipeline failed: {response}")
    if manual_only and pipeline.get("stage") != "pending_approval":
        raise RuntimeError(f"n8n full pipeline manual check did not stop at pending approval: {pipeline}")
    return pipeline


def run_acceptance(args: argparse.Namespace) -> dict[str, Any]:
    if args.base_dir:
        run_base = Path(args.base_dir)
        if not run_base.is_absolute():
            run_base = ROOT / run_base
        base_dir = run_base / f"acceptance_{timestamp()}"
        base_dir.mkdir(parents=True, exist_ok=False)
        db_path = base_dir / "agent_ops.sqlite3"
        log_path = base_dir / "operation_log.jsonl"
    else:
        base_dir = ROOT / "runs"
        db_path = ROOT / "runs" / "acceptance_ops.sqlite3"
        log_path = ROOT / "runs" / "acceptance_operation_log.jsonl"

    n8n_headers: dict[str, str] = {}
    if args.via_n8n or args.via_n8n_full:
        secret = _webhook_secret(args.env_file)
        if not secret:
            raise RuntimeError("N8N_WEBHOOK_SECRET is required in .env to run --via-n8n acceptance.")
        n8n_headers = {"X-Bakery-Webhook-Secret": secret}
    if args.via_n8n_full:
        _preflight_full_pipeline_runtime(getattr(args, "n8n_db", ""))
        pipeline = _run_full_pipeline_via_n8n(args, n8n_headers)
        package_dir = resolve_path(pipeline["package_dir"])
        final_metadata = read_json(package_dir / "metadata.json", {})
        manual_only = bool(getattr(args, "manual_only", False))
        return {
            "ok": bool(pipeline.get("ok")),
            "mode": "n8n_full_pipeline_manual_check" if manual_only else "n8n_full_pipeline_acceptance",
            "base_dir": str(ROOT / "runs"),
            "isolated": False,
            "db": str(ROOT / "data" / "agent_ops.sqlite3"),
            "log": str(ROOT / "runs" / "operation_log.jsonl"),
            "via_n8n": True,
            "via_n8n_full": True,
            "manual_only": manual_only,
            "request": args.request,
            "run_id": pipeline["run_id"],
            "package_dir": str(package_dir),
            "content_task": pipeline.get("operation", {}).get("content_task", {}),
            "stage": pipeline.get("stage", ""),
            "approval_required": bool(pipeline.get("approval_required")),
            "next_action": pipeline.get("next_action", {}),
            "approval": pipeline.get("approval", {}),
            "image_generation": pipeline.get("image_generation", {}),
            "image_selection": pipeline.get("image_selection", {}),
            "publish_draft": pipeline.get("publish_draft", {}),
            "publish_records": pipeline.get("publish_records", []),
            "mock_publish_results": pipeline.get("mock_publish_results", []),
            "final": {
                "approval_status": final_metadata.get("approval_status", final_metadata.get("status", "")),
                "image_status": final_metadata.get("image_status", ""),
                "selected_image_id": final_metadata.get("selected_image_id", ""),
                "publish_status": final_metadata.get("publish_status", ""),
                "publish_record_count": len(final_metadata.get("publish_records", [])),
                "platforms": _platforms(final_metadata.get("platform", "")),
                "mock_publish_used": bool(args.mock_publish),
            },
        }
    if args.via_n8n:
        operation = _run_content_operation_via_n8n(args, n8n_headers)
        db_path = ROOT / "data" / "agent_ops.sqlite3"
        base_dir = ROOT / "runs"
        log_path = ROOT / "runs" / "operation_log.jsonl"
    else:
        operation = _run_content_operation(args, base_dir, db_path, log_path)
    package_ref = str(operation["approval_package"])
    package_dir = resolve_path(package_ref)
    run_id = package_dir.name

    if args.via_n8n:
        approval_response = _post_json(
            ops_dashboard.APPROVAL_REVIEW_WEBHOOK,
            {"package": package_ref, "status": "approved", "note": args.approval_note, "create_revision": False},
            args.timeout,
            n8n_headers,
        )
        approval = approval_response.get("approval", {})
        image_response = _post_json(
            ops_dashboard.IMAGE_GENERATION_WEBHOOK,
            {"package": package_ref, "local_demo": True, "n": 1, "out_dir": "runs/generated_images"},
            args.timeout,
            n8n_headers,
        )
        image_generation = image_response.get("image_generation", {})
    else:
        approval = approval_service.update_approval_status(package_dir, "approved", args.approval_note)
        with db_service.get_connection(db_path) as conn:
            db_sync_service.sync_package(conn, package_dir)
        image_generation = image_generation_service.generate_for_package(
            package_dir,
            out_dir=base_dir / "generated_images",
            live=False,
            require_key=False,
            n=1,
            local_demo=True,
            db=db_path,
            allow_unapproved=False,
        )
    metadata = read_json(package_dir / "metadata.json", {})
    image_id = _choose_image_id(metadata, args.preferred_image_id)
    if args.via_n8n:
        selection_response = _post_json(
            ops_dashboard.IMAGE_SELECTION_WEBHOOK,
            {"package": package_ref, "image_id": image_id, "note": args.image_note},
            args.timeout,
            n8n_headers,
        )
        image_selection = selection_response.get("image_selection", {})
        draft_response = _post_json(
            ops_dashboard.PUBLISH_DRAFT_WEBHOOK,
            {"package": package_ref, "out_dir": "runs/publish_drafts"},
            args.timeout,
            n8n_headers,
        )
        publish_draft = draft_response.get("publish_draft", {})
    else:
        image_selection = image_selection_service.select_image_variant(package_dir, image_id, note=args.image_note, db=db_path)
        publish_draft = publish_service.prepare_publish_draft(package_dir, out_dir=base_dir / "publish_drafts", db=db_path)

    publish_records = []
    mock_publish_results = []
    for platform in _platforms(args.platforms):
        if args.mock_publish and args.via_n8n:
            mock_response = _post_json(
                ops_dashboard.PUBLISH_MOCK_WEBHOOK,
                {"package": package_ref, "platform": platform},
                args.timeout,
                n8n_headers,
            )
            mock_result = mock_response.get("mock_publish", {})
            mock_publish_results.append(mock_result)
            publish_records.append(mock_result.get("publish_record", {}))
        elif args.mock_publish:
            mock_result = publisher_service.mock_publish(
                package_dir,
                platform=platform,
                db=db_path,
                env_file=args.env_file,
            )
            mock_publish_results.append(mock_result)
            publish_records.append(mock_result["publish_record"])
        elif args.via_n8n:
            record_response = _post_json(
                ops_dashboard.PUBLISH_RECORD_WEBHOOK,
                {
                    "package": package_ref,
                    "platform": platform,
                    "published_url": f"https://example.com/{platform}/{run_id}",
                    "note": f"n8n acceptance verification record for {platform}.",
                },
                args.timeout,
                n8n_headers,
            )
            publish_records.append(record_response.get("publish_record", {}))
        else:
            publish_records.append(
                publish_service.record_manual_publish(
                    package_dir,
                    platform=platform,
                    published_url=f"https://example.com/{platform}/{run_id}",
                    note=f"Acceptance verification record for {platform}.",
                    db=db_path,
                )
            )

    final_metadata = read_json(package_dir / "metadata.json", {})
    result = {
        "ok": final_metadata.get("publish_status") == "published",
        "mode": "n8n_acceptance" if args.via_n8n else "local_acceptance",
        "base_dir": str(base_dir),
        "isolated": bool(args.base_dir),
        "db": str(db_path),
        "log": str(log_path),
        "via_n8n": bool(args.via_n8n),
        "request": args.request,
        "run_id": run_id,
        "package_dir": str(package_dir),
        "content_task": operation.get("content_task", {}),
        "approval": approval,
        "image_generation": image_generation,
        "image_selection": image_selection,
        "publish_draft": publish_draft,
        "publish_records": publish_records,
        "mock_publish_results": mock_publish_results,
        "final": {
            "approval_status": final_metadata.get("approval_status", final_metadata.get("status", "")),
            "image_status": final_metadata.get("image_status", ""),
            "selected_image_id": final_metadata.get("selected_image_id", ""),
            "publish_status": final_metadata.get("publish_status", ""),
            "publish_record_count": len(final_metadata.get("publish_records", [])),
            "platforms": _platforms(final_metadata.get("platform", "")),
            "mock_publish_used": bool(args.mock_publish),
        },
    }
    if not result["ok"]:
        raise RuntimeError(f"Acceptance run did not reach published status: {result['final']}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a V2 acceptance chain from plain request to recorded publish state.")
    parser.add_argument("--request", default=DEFAULT_REQUEST)
    parser.add_argument("--platforms", default="xiaohongshu,douyin")
    parser.add_argument("--image-count", type=int, default=3)
    parser.add_argument("--preferred-image-id", default="deconstructed")
    parser.add_argument("--approval-note", default="Acceptance approval after local review.")
    parser.add_argument("--image-note", default="Acceptance selected image variant.")
    parser.add_argument("--base-dir", default="", help="Optional isolated output base. Defaults to existing runs/data paths.")
    parser.add_argument("--via-n8n", action="store_true", help="Execute each acceptance step through active n8n webhooks.")
    parser.add_argument("--via-n8n-full", action="store_true", help="Execute the complete chain through the single n8n full pipeline webhook.")
    parser.add_argument("--manual-only", action="store_true", help="With --via-n8n-full, verify the production default stops at pending human approval.")
    parser.add_argument("--mock-publish", action="store_true", help="Use the safe mock publisher connector instead of manual publish record payloads. Requires MOCK_PUBLISH_ENABLED=true.")
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--n8n-db", default="", help="Optional exported n8n SQLite DB for preflight checks before --via-n8n-full.")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = run_acceptance(args)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Acceptance ok: {result['ok']}")
        print(f"Run: {result['run_id']}")
        print(f"Package: {result['package_dir']}")
        print(f"Final: {json.dumps(result['final'], ensure_ascii=False)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
