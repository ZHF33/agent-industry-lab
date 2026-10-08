#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services import approval_service, db_service, db_sync_service, image_generation_service, image_selection_service, image_service, publish_service, publisher_service, revision_service
from services.common import load_dotenv, read_json, resolve_path, write_json

MAX_IMAGE_COUNT = 8


def _expected_token() -> str:
    env = load_dotenv(".env")
    return (os.environ.get("AGENT_API_TOKEN") or env.get("AGENT_API_TOKEN") or "").strip()


def _env_bool(name: str, env_file: str | Path = ".env") -> bool:
    env = load_dotenv(env_file)
    return (os.environ.get(name) or env.get(name) or "").strip().lower() in {"1", "true", "yes"}


def _authorized(handler: BaseHTTPRequestHandler) -> bool:
    expected = _expected_token()
    if not expected:
        return False
    auth = handler.headers.get("Authorization", "")
    token = auth.removeprefix("Bearer ").strip() if auth.startswith("Bearer ") else handler.headers.get("X-Agent-Api-Token", "").strip()
    return token == expected


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _read_json(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    raw_length = handler.headers.get("Content-Length", "0")
    try:
        length = int(raw_length)
    except ValueError:
        raise ValueError("Invalid Content-Length")
    if length <= 0:
        return {}
    if length > 64_000:
        raise ValueError("Request body too large")
    raw = handler.rfile.read(length)
    try:
        data = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON body: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("JSON body must be an object")
    return data


def _workspace_path(value: str | Path, label: str) -> Path:
    path = resolve_path(value)
    try:
        path.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError(f"{label} must stay inside workspace root: {ROOT}") from exc
    return path


def _build_command(payload: dict[str, Any]) -> list[str]:
    request = str(payload.get("user_request") or payload.get("request") or payload.get("natural_request") or "").strip()
    mode = str(payload.get("execution_mode") or payload.get("mode") or "dry-run")
    if mode not in {"dry-run", "live-dify"}:
        raise ValueError("execution_mode must be dry-run or live-dify")
    image_count = int(payload.get("image_count") or 3)
    if image_count < 1 or image_count > MAX_IMAGE_COUNT:
        raise ValueError(f"image_count must be between 1 and {MAX_IMAGE_COUNT}")

    command = [
        sys.executable,
        str(ROOT / "scripts" / "run_content_operation.py"),
        "--mode",
        mode,
        "--campaign-name",
        str(payload.get("campaign_name") or "Webhook Bakery Content Operation"),
        "--platform",
        str(payload.get("platforms") or payload.get("platform") or "xiaohongshu,douyin"),
        "--constraints",
        str(
            payload.get("constraints")
            or "No fake price, inventory, sales volume, health claims, nutrition claims, official authorization, logo, trademark, or embedded text."
        ),
        "--image-count",
        str(image_count),
    ]
    if request:
        command.extend(["--request", request])
    else:
        for source, flag in [
            ("product_name", "--product-query"),
            ("campaign_goal", "--campaign-goal"),
            ("content_type", "--content-type"),
            ("image_type", "--image-type"),
            ("image_style", "--image-style"),
            ("audience", "--audience"),
        ]:
            value = payload.get(source)
            if value:
                command.extend([flag, str(value)])
    if payload.get("skip_image"):
        command.append("--skip-image")
    if payload.get("live_image"):
        raise ValueError("live_image is not allowed through /operation. Approve the package first, then call /image/generate.")
    optional_paths = [
        ("db", "--db"),
        ("db_path", "--db"),
        ("out_dir", "--out-dir"),
        ("approval_out_dir", "--approval-out-dir"),
        ("image_out_dir", "--image-out-dir"),
        ("archive_out_dir", "--archive-out-dir"),
        ("log", "--log"),
    ]
    seen_flags: set[str] = set()
    for source, flag in optional_paths:
        if flag in seen_flags or not payload.get(source):
            continue
        command.extend([flag, str(_workspace_path(payload[source], source))])
        seen_flags.add(flag)
    return command


def run_operation(payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    command = _build_command(payload)
    completed = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=timeout,
        check=False,
    )
    operation: dict[str, Any] = {}
    if completed.stdout.strip():
        try:
            operation = json.loads(completed.stdout)
        except json.JSONDecodeError:
            operation = {"raw_stdout": completed.stdout}
    return {
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "operation": operation,
        "stderr": completed.stderr[-4000:],
    }


def update_approval(payload: dict[str, Any]) -> dict[str, Any]:
    package_value = str(payload.get("package") or payload.get("package_dir") or payload.get("package_path") or "").strip()
    if not package_value:
        raise ValueError("package is required")
    status = str(payload.get("status") or payload.get("approval_status") or "").strip()
    if not status:
        raise ValueError("status is required")
    note = str(payload.get("note") or payload.get("reviewer_note") or "")
    db_value = payload.get("db") or payload.get("db_path") or db_service.DEFAULT_DB

    package_dir = _workspace_path(package_value, "package")
    result = approval_service.update_approval_status(package_dir, status, note)
    db_path = _workspace_path(db_value, "db")
    with db_service.get_connection(db_path) as conn:
        synced = db_sync_service.sync_package(conn, package_dir)
    result["db_sync_status"] = "synced" if synced else "skipped"
    result["db"] = str(db_path)
    return {"ok": True, "approval": result}


def create_revision(payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    package_value = str(payload.get("package") or payload.get("package_dir") or payload.get("package_path") or "").strip()
    if not package_value:
        raise ValueError("package is required")
    note = str(payload.get("note") or payload.get("revision_note") or "")
    out_dir = _workspace_path(payload.get("out_dir") or "runs/revisions", "out_dir")
    live = bool(payload.get("live"))
    db_value = payload.get("db") or payload.get("db_path") or db_service.DEFAULT_DB

    package_dir = _workspace_path(package_value, "package")
    db_path = _workspace_path(db_value, "db")
    prepared = revision_service.create_revision_request(package_dir, note=note, out_dir=out_dir)
    response = revision_service.call_dify_revision_workflow(prepared["payload"], dry_run=not live, timeout=timeout)
    output_path = ""
    if live:
        out = Path(prepared["revision_request"]).with_name(Path(prepared["revision_request"]).name.replace("_request_", "_output_"))
        write_json(out, response)
        output_path = str(out)
    with db_service.get_connection(db_path) as conn:
        synced = db_sync_service.sync_package(conn, Path(prepared["package_dir"]))
    return {
        "ok": True,
        "revision": {
            "mode": "live" if live else "dry_run",
            "package_dir": prepared["package_dir"],
            "revision_request": prepared["revision_request"],
            "revision_output": output_path,
            "approval_status": "pending_revision_review",
            "db_sync_status": "synced" if synced else "skipped",
            "db": str(db_path),
        },
    }


def review_package(payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    approval = update_approval(payload)["approval"]
    status = approval["status"]
    result: dict[str, Any] = {"ok": True, "approval": approval, "revision": None}
    if bool(payload.get("create_revision")):
        if status not in {"needs_revision", "rejected", "pending_revision_review"}:
            raise ValueError("create_revision requires status needs_revision, rejected, or pending_revision_review")
        revision_payload = {**payload, "package": approval["package_dir"]}
        result["revision"] = create_revision(revision_payload, timeout)["revision"]
    return result


def generate_images(payload: dict[str, Any]) -> dict[str, Any]:
    package_value = str(payload.get("package") or payload.get("package_dir") or payload.get("package_path") or "").strip()
    if not package_value:
        raise ValueError("package is required")
    live = bool(payload.get("live") or payload.get("live_image"))
    local_demo = bool(payload.get("local_demo"))
    if live and local_demo:
        raise ValueError("live and local_demo cannot both be true.")
    if live and not _env_bool("AGENT_API_ALLOW_LIVE_IMAGE", payload.get("env_file") or ".env"):
        raise ValueError("live image generation is disabled for Agent API. Set AGENT_API_ALLOW_LIVE_IMAGE=true to allow it.")
    out_dir = _workspace_path(payload.get("out_dir") or image_service.DEFAULT_OUT_DIR, "out_dir")
    db_path = _workspace_path(payload.get("db") or payload.get("db_path") or db_service.DEFAULT_DB, "db")
    image_count = int(payload.get("n") or 1)
    if image_count < 1 or image_count > MAX_IMAGE_COUNT:
        raise ValueError(f"n must be between 1 and {MAX_IMAGE_COUNT}")
    result = image_generation_service.generate_for_package(
        _workspace_path(package_value, "package"),
        out_dir=out_dir,
        live=live,
        require_key=bool(payload.get("require_key")),
        n=image_count,
        local_demo=local_demo,
        db=db_path,
        allow_unapproved=False,
        raise_on_failure=False,
    )
    return {"ok": result["ok"], "image_generation": {**result["image_generation"], "package_dir": result["package_dir"], "run_id": result["run_id"], "approval_status": result["approval_status"], "db_sync_status": result["db_sync_status"], "db": result["db"]}, "error": result.get("error", "")}


def select_image(payload: dict[str, Any]) -> dict[str, Any]:
    package_value = str(payload.get("package") or payload.get("package_dir") or payload.get("package_path") or "").strip()
    if not package_value:
        raise ValueError("package is required")
    image_id = str(payload.get("image_id") or payload.get("variant_id") or "").strip()
    if not image_id:
        raise ValueError("image_id is required")
    db_path = _workspace_path(payload.get("db") or payload.get("db_path") or db_service.DEFAULT_DB, "db")
    result = image_selection_service.select_image_variant(
        _workspace_path(package_value, "package"),
        image_id,
        note=str(payload.get("note") or payload.get("selection_note") or ""),
        db=db_path,
        sync_db=not bool(payload.get("no_sync_db")),
    )
    return {"ok": True, "image_selection": result}


def prepare_publish_draft(payload: dict[str, Any]) -> dict[str, Any]:
    package_value = str(payload.get("package") or payload.get("package_dir") or payload.get("package_path") or "").strip()
    if not package_value:
        raise ValueError("package is required")
    package_dir = _workspace_path(package_value, "package")
    out_dir = _workspace_path(payload.get("out_dir") or "runs/publish_drafts", "out_dir")
    db_path = _workspace_path(payload.get("db") or payload.get("db_path") or db_service.DEFAULT_DB, "db")
    result = publish_service.prepare_publish_draft(
        package_dir,
        out_dir=out_dir,
        db=db_path,
        sync_db=not bool(payload.get("no_sync_db")),
    )
    return {"ok": True, "publish_draft": result}


def record_publish(payload: dict[str, Any]) -> dict[str, Any]:
    package_value = str(payload.get("package") or payload.get("package_dir") or payload.get("package_path") or "").strip()
    if not package_value:
        raise ValueError("package is required")
    platform = str(payload.get("platform") or "").strip()
    if not platform:
        raise ValueError("platform is required")
    result = publish_service.record_manual_publish(
        _workspace_path(package_value, "package"),
        platform=platform,
        published_url=str(payload.get("published_url") or payload.get("url") or ""),
        note=str(payload.get("note") or ""),
        published_at=str(payload.get("published_at") or ""),
        metrics=payload.get("metrics") if isinstance(payload.get("metrics"), dict) else payload,
        db=_workspace_path(payload.get("db") or payload.get("db_path") or db_service.DEFAULT_DB, "db"),
        sync_db=not bool(payload.get("no_sync_db")),
    )
    return {"ok": True, "publish_record": result}


def mock_publish(payload: dict[str, Any]) -> dict[str, Any]:
    package_value = str(payload.get("package") or payload.get("package_dir") or payload.get("package_path") or "").strip()
    if not package_value:
        raise ValueError("package is required")
    platform = str(payload.get("platform") or "").strip()
    if not platform:
        raise ValueError("platform is required")
    result = publisher_service.mock_publish(
        _workspace_path(package_value, "package"),
        platform=platform,
        db=_workspace_path(payload.get("db") or payload.get("db_path") or db_service.DEFAULT_DB, "db"),
        env_file=payload.get("env_file") or ".env",
        sync_db=not bool(payload.get("no_sync_db")),
    )
    return {"ok": True, "mock_publish": result}


def _platforms(value: Any) -> list[str]:
    return [item.strip() for item in str(value or "").split(",") if item.strip()] or ["xiaohongshu"]


def _choose_image_id(package_dir: Path, preferred: str) -> str:
    metadata = read_json(package_dir / "metadata.json", {})
    image_asset = metadata.get("assets", {}).get("image_generation", {})
    images = image_asset.get("images", []) if isinstance(image_asset, dict) else []
    image_ids = [str(image.get("image_id", "")) for image in images if isinstance(image, dict) and image.get("image_id")]
    if not image_ids:
        raise ValueError("Pipeline did not produce image variants.")
    return preferred if preferred in image_ids else image_ids[0]


def run_pipeline(payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    if not str(payload.get("user_request") or payload.get("request") or payload.get("natural_request") or "").strip():
        raise ValueError("user_request is required for /pipeline.")
    db_path = _workspace_path(payload.get("db") or payload.get("db_path") or db_service.DEFAULT_DB, "db")
    operation_payload = {
        **payload,
        "execution_mode": payload.get("execution_mode") or payload.get("mode") or "dry-run",
        "db": str(db_path),
        "out_dir": payload.get("out_dir") or "runs/operations",
        "approval_out_dir": payload.get("approval_out_dir") or "runs/approval_queue",
        "image_out_dir": payload.get("image_out_dir") or "runs/generated_images",
        "archive_out_dir": payload.get("archive_out_dir") or "runs/operation_archive",
        "log": payload.get("log") or "runs/operation_log.jsonl",
    }
    operation_response = run_operation(operation_payload, timeout)
    if not operation_response.get("ok"):
        return {"ok": False, "stage": "operation", **operation_response}

    operation = operation_response.get("operation", {})
    package_ref = str(operation.get("approval_package") or "")
    if not package_ref:
        raise ValueError("Pipeline operation did not return approval_package.")
    package_dir = _workspace_path(package_ref, "package")
    approval_mode = str(payload.get("approval_mode") or ("auto" if payload.get("auto_approve") else "manual")).strip().lower()
    if approval_mode not in {"manual", "auto"}:
        raise ValueError("approval_mode must be manual or auto.")
    if approval_mode == "manual":
        metadata = read_json(package_dir / "metadata.json", {})
        return {
            "ok": True,
            "stage": "pending_approval",
            "approval_required": True,
            "run_id": package_dir.name,
            "package_dir": str(package_dir),
            "operation": operation,
            "approval": {
                "status": metadata.get("approval_status", metadata.get("status", "pending")),
                "package_dir": str(package_dir),
            },
            "next_action": {
                "action": "human_review",
                "webhook": "v2ApprovalReviewWebhook",
                "suggested_payload": {"package": str(package_dir), "status": "approved", "note": "Approved after human review.", "create_revision": False},
            },
            "final": {
                "approval_status": metadata.get("approval_status", metadata.get("status", "")),
                "image_status": metadata.get("image_status", ""),
                "selected_image_id": metadata.get("selected_image_id", ""),
                "publish_status": metadata.get("publish_status", ""),
                "publish_record_count": len(metadata.get("publish_records", [])),
            },
        }

    approval = update_approval(
        {
            "package": str(package_dir),
            "status": payload.get("approval_status") or "approved",
            "note": payload.get("approval_note") or "Pipeline auto-approved because approval_mode=auto was explicitly requested.",
            "db": str(db_path),
        }
    )["approval"]

    image_generation = generate_images(
        {
            "package": str(package_dir),
            "local_demo": bool(payload.get("local_demo", True)),
            "live": bool(payload.get("live_image") or payload.get("live")),
            "n": int(payload.get("n") or 1),
            "out_dir": payload.get("image_out_dir") or "runs/generated_images",
            "db": str(db_path),
            "env_file": payload.get("env_file") or ".env",
        }
    )["image_generation"]
    image_id = _choose_image_id(package_dir, str(payload.get("preferred_image_id") or "deconstructed"))
    image_selection = select_image(
        {
            "package": str(package_dir),
            "image_id": image_id,
            "note": payload.get("image_note") or "Pipeline selected preferred image variant.",
            "db": str(db_path),
        }
    )["image_selection"]
    publish_draft = prepare_publish_draft(
        {
            "package": str(package_dir),
            "out_dir": payload.get("publish_out_dir") or "runs/publish_drafts",
            "db": str(db_path),
        }
    )["publish_draft"]

    publish_records = []
    mock_publish_results = []
    use_mock_publish = bool(payload.get("mock_publish"))
    for platform in _platforms(payload.get("platforms") or payload.get("platform") or "xiaohongshu,douyin"):
        if use_mock_publish:
            mock_result = mock_publish(
                {
                    "package": str(package_dir),
                    "platform": platform,
                    "db": str(db_path),
                    "env_file": payload.get("env_file") or ".env",
                }
            )["mock_publish"]
            mock_publish_results.append(mock_result)
            publish_records.append(mock_result.get("publish_record", {}))
        else:
            publish_records.append(
                record_publish(
                    {
                        "package": str(package_dir),
                        "platform": platform,
                        "published_url": f"https://example.com/{platform}/{package_dir.name}",
                        "note": "Manual publish record created by pipeline; external platform posting remains operator-owned.",
                        "db": str(db_path),
                    }
                )["publish_record"]
            )

    final_metadata = read_json(package_dir / "metadata.json", {})
    return {
        "ok": final_metadata.get("publish_status") == "published",
        "stage": "completed",
        "run_id": package_dir.name,
        "package_dir": str(package_dir),
        "operation": operation,
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
        },
    }


class AgentRequestHandler(BaseHTTPRequestHandler):
    timeout_seconds = 360

    def do_GET(self) -> None:
        if self.path.rstrip("/") == "/health":
            _json_response(self, 200, {"ok": True, "service": "bakery-agent-api"})
            return
        if self.path.rstrip("/") == "/image/readiness":
            _json_response(self, 200, {"ok": True, "image_readiness": image_service.live_image_readiness(require_agent_api_allow=True)})
            return
        _json_response(self, 404, {"ok": False, "error": "Not found"})

    def do_POST(self) -> None:
        route = self.path.rstrip("/")
        if route not in {"/operation", "/pipeline", "/approval/status", "/approval/review", "/revision", "/image/generate", "/image/select", "/publish/draft", "/publish/record", "/publish/mock"}:
            _json_response(self, 404, {"ok": False, "error": "Not found"})
            return
        if not _authorized(self):
            _json_response(self, 401, {"ok": False, "error": "Unauthorized"})
            return
        try:
            payload = _read_json(self)
            if route == "/operation":
                result = run_operation(payload, self.timeout_seconds)
            elif route == "/pipeline":
                result = run_pipeline(payload, self.timeout_seconds)
            elif route == "/approval/status":
                result = update_approval(payload)
            elif route == "/approval/review":
                result = review_package(payload, self.timeout_seconds)
            elif route == "/revision":
                result = create_revision(payload, self.timeout_seconds)
            elif route == "/image/generate":
                result = generate_images(payload)
            elif route == "/image/select":
                result = select_image(payload)
            elif route == "/publish/draft":
                result = prepare_publish_draft(payload)
            elif route == "/publish/record":
                result = record_publish(payload)
            else:
                result = mock_publish(payload)
        except subprocess.TimeoutExpired:
            _json_response(self, 504, {"ok": False, "error": "Operation timed out"})
            return
        except Exception as exc:
            _json_response(self, 400, {"ok": False, "error": str(exc)})
            return
        _json_response(self, 200 if result["ok"] else 500, result)

    def log_message(self, format: str, *args: Any) -> None:
        if sys.stderr:
            sys.stderr.write("%s - %s\n" % (self.address_string(), format % args))


def main() -> int:
    parser = argparse.ArgumentParser(description="Local HTTP API for n8n to trigger Bakery AI Agent V2 operations.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--timeout", type=int, default=360)
    args = parser.parse_args()
    AgentRequestHandler.timeout_seconds = args.timeout
    server = ThreadingHTTPServer((args.host, args.port), AgentRequestHandler)
    if sys.stdout:
        print(json.dumps({"ok": True, "service": "bakery-agent-api", "url": f"http://{args.host}:{args.port}"}, ensure_ascii=False), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
