from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from . import dify_client
from .common import load_dotenv, now_iso, read_json, resolve_path, timestamp, write_json


def build_revision_payload(metadata: dict[str, Any], previous_outputs: dict[str, Any], notes: list[str]) -> dict[str, Any]:
    content_task = metadata.get("content_task") or {}
    product_name = content_task.get("product_name") or metadata.get("product_name", "bakery product")
    campaign_goal = content_task.get("campaign_goal") or metadata.get("content_goal", "Revise review-ready bakery content.")
    revision_context = {
        "approval_status": metadata.get("approval_status", metadata.get("status", "")),
        "content_task": content_task,
        "review_notes": notes,
        "previous_outputs": previous_outputs,
        "required_revision_policy": [
            "Only revise the parts called out by reviewer notes; keep approved sections stable.",
            "Remove or replace any logo, trademark, official packaging, official authorization implication, embedded text, or misleading brand asset.",
            "Keep all outputs review-ready; do not add automatic publishing instructions.",
            "Do not add fake price, inventory, sales volume, nutrition, health effects, origin, or ingredient claims.",
            "Image and video prompts must follow the current content_task product_name, image_type, and image_style.",
        ],
    }
    return {
        "inputs": {
            "product_query": product_name,
            "product_name": product_name,
            "content_type": content_task.get("content_type", ""),
            "image_type": content_task.get("image_type", ""),
            "image_style": content_task.get("image_style", ""),
            "platforms": content_task.get("platforms", metadata.get("platform", "")),
            "audience": content_task.get("audience", ""),
            "constraints": content_task.get("constraints", ""),
            "content_task_json": json.dumps(content_task, ensure_ascii=False),
            "campaign_goal": f"{campaign_goal} Revise according to human review notes.",
            "product_knowledge": json.dumps(revision_context, ensure_ascii=False, indent=2),
            "brand_context": "Local bakery operation. Use only provided facts; do not imply external official authorization.",
            "platform_rules": "No auto-publishing; no health claims; no fake price, inventory, origin, nutrition, logo, trademark, official packaging, or absolute claims.",
            "date": now_iso()[:10],
        },
        "response_mode": "blocking",
        "user": "local-bakery-revision",
    }


def save_revision_request(package_dir: str | Path, payload: dict[str, Any], out_dir: str | Path = "runs/revisions") -> Path:
    package = resolve_path(package_dir)
    target = resolve_path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    path = target / f"{package.name}_revision_request_{timestamp()}.json"
    write_json(path, payload)
    revisions = read_json(package / "revision_requests.json", [])
    entry = {"created_at": now_iso(), "revision_request": str(path), "status": "prepared"}
    revisions.append(entry)
    write_json(package / "revision_requests.json", revisions)
    metadata = read_json(package / "metadata.json", {})
    metadata.setdefault("revisions", []).append(entry)
    metadata["status"] = "pending_revision_review"
    metadata["approval_status"] = "pending_revision_review"
    metadata["updated_at"] = now_iso()
    write_json(package / "metadata.json", metadata)
    return path


def create_revision_request(package_dir: str | Path, note: str = "", out_dir: str | Path = "runs/revisions") -> dict[str, Any]:
    package = resolve_path(package_dir)
    metadata = read_json(package / "metadata.json", {})
    if metadata.get("status", metadata.get("approval_status", "")) not in {"needs_revision", "rejected", "pending_revision_review"}:
        raise RuntimeError("Revision requires package status needs_revision, rejected, or pending_revision_review")
    source_output = read_json(metadata.get("source_output", ""), {}) if metadata.get("source_output") else {}
    outputs = source_output.get("data", {}).get("outputs", {})
    notes = [item.get("note", "") for item in metadata.get("review_notes", []) if item.get("note")]
    if note:
        notes.append(note)
    payload = build_revision_payload(metadata, outputs, notes)
    request_path = save_revision_request(package, payload, out_dir)
    return {"package_dir": str(package), "revision_request": str(request_path), "payload": payload}


def call_dify_revision_workflow(payload: dict[str, Any], *, dry_run: bool = True, timeout: int = 240) -> dict[str, Any]:
    if dry_run:
        return {"mode": "dry_run", "status": "prepared", "payload": payload}
    env = load_dotenv(".env")
    base_url = env.get("DIFY_BASE_URL") or os.environ.get("DIFY_BASE_URL", "")
    api_key = env.get("DIFY_API_KEY") or os.environ.get("DIFY_API_KEY", "")
    if not base_url or not api_key:
        raise RuntimeError("DIFY_BASE_URL and DIFY_API_KEY are required for live revision")
    return dify_client.call_workflow(base_url, api_key, payload, timeout, label="Dify revision")
