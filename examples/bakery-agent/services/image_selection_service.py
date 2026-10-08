from __future__ import annotations

from pathlib import Path
from typing import Any

from . import approval_service, db_service, db_sync_service
from .common import now_iso, read_json, resolve_path, write_json


def _find_image(images: list[dict[str, Any]], image_id: str) -> dict[str, Any]:
    for image in images:
        if str(image.get("image_id", "")) == image_id:
            return image
    raise RuntimeError(f"Image variant not found: {image_id}")


def _update_prompt_variants(prompt: dict[str, Any], image_id: str) -> dict[str, Any]:
    variants = prompt.get("variants", [])
    if not isinstance(variants, list) or not variants:
        raise RuntimeError("No image variants found in enhanced_image_prompt.json")
    matched = False
    for variant in variants:
        if not isinstance(variant, dict):
            continue
        variant_id = str(variant.get("variant_id") or variant.get("image_id") or "")
        if variant_id == image_id:
            variant["review_status"] = "selected"
            variant["selected"] = True
            matched = True
        else:
            variant["review_status"] = "not_selected"
            variant["selected"] = False
    if not matched:
        raise RuntimeError(f"Image variant not found in prompt variants: {image_id}")
    prompt["selected_variant_id"] = image_id
    prompt["updated_at"] = now_iso()
    return prompt


def select_image_variant(
    package_dir: str | Path,
    image_id: str,
    *,
    note: str = "",
    db: str | Path = db_service.DEFAULT_DB,
    sync_db: bool = True,
) -> dict[str, Any]:
    package_path = resolve_path(package_dir)
    metadata = read_json(package_path / "metadata.json", {})
    if not metadata:
        raise RuntimeError(f"Approval package metadata not found: {package_path}")
    image_asset = metadata.get("assets", {}).get("image_generation", {})
    images = image_asset.get("images", [])
    if not isinstance(images, list) or not images:
        raise RuntimeError("No generated or prepared image variants found in approval package metadata.")

    selected = _find_image(images, image_id)
    selected_at = now_iso()
    for image in images:
        if str(image.get("image_id", "")) == image_id:
            image["review_status"] = "selected"
            image["selected"] = True
            image["selected_at"] = selected_at
            if note:
                image["selection_note"] = note
        else:
            image["review_status"] = "not_selected"
            image["selected"] = False

    image_asset["selected_image_id"] = image_id
    image_asset["selected_image"] = selected
    image_asset["review_status"] = "selected"
    image_asset["updated_at"] = selected_at
    metadata["selected_image_id"] = image_id
    metadata["selected_image"] = selected
    metadata["image_review_status"] = "selected"
    metadata["updated_at"] = selected_at
    metadata.setdefault("review_notes", []).append(
        {
            "created_at": selected_at,
            "status": "image_selected",
            "note": note or f"Selected image variant {image_id}.",
            "image_id": image_id,
        }
    )
    write_json(package_path / "metadata.json", metadata)

    prompt_path = package_path / "enhanced_image_prompt.json"
    prompt = _update_prompt_variants(read_json(prompt_path, {}), image_id)
    write_json(prompt_path, prompt)

    approval_service.append_review_note(package_path, "image_selected", note or f"Selected image variant {image_id}.")
    approval_service.write_product_flow(package_path, metadata, image_prompt=prompt)

    synced = False
    if sync_db:
        with db_service.get_connection(db) as conn:
            synced = db_sync_service.sync_package(conn, package_path)

    return {
        "status": "selected",
        "package_dir": str(package_path),
        "run_id": metadata.get("run_id", package_path.name),
        "product_name": metadata.get("product_name", ""),
        "image_id": image_id,
        "selected_image": selected,
        "db_sync_status": "synced" if synced else "skipped",
        "db": str(resolve_path(db)),
    }
