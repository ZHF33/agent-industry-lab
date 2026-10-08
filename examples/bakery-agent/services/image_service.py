from __future__ import annotations

import base64
import json
import os
import struct
import urllib.error
import urllib.request
import zlib
from pathlib import Path
from typing import Any

from .common import load_dotenv, now_iso, read_json, resolve_path, timestamp, write_json

DEFAULT_INPUT = "runs/bakery_latest_image_prompt.json"
DEFAULT_OUT_DIR = "runs/generated_images"
DEFAULT_IMAGE_MODEL = "gpt-image-2"
DEFAULT_IMAGE_SIZE = "1024x1024"
DEFAULT_IMAGE_QUALITY = "low"


def _parse_size(value: str) -> tuple[int, int]:
    try:
        width, height = str(value).lower().split("x", 1)
        return max(128, int(width)), max(128, int(height))
    except Exception:
        return 1024, 1024


def _png_chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def _write_png(path: Path, width: int, height: int, pixels: bytearray) -> None:
    rows = bytearray()
    stride = width * 3
    for y in range(height):
        rows.append(0)
        start = y * stride
        rows.extend(pixels[start : start + stride])
    raw = b"\x89PNG\r\n\x1a\n"
    raw += _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    raw += _png_chunk(b"IDAT", zlib.compress(bytes(rows), level=6))
    raw += _png_chunk(b"IEND", b"")
    path.write_bytes(raw)


def _fill_rect(pixels: bytearray, width: int, height: int, x0: int, y0: int, x1: int, y1: int, color: tuple[int, int, int]) -> None:
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(width, x1), min(height, y1)
    for y in range(y0, y1):
        row = y * width * 3
        for x in range(x0, x1):
            idx = row + x * 3
            pixels[idx : idx + 3] = bytes(color)


def _fill_ellipse(pixels: bytearray, width: int, height: int, cx: int, cy: int, rx: int, ry: int, color: tuple[int, int, int]) -> None:
    if rx <= 0 or ry <= 0:
        return
    for y in range(max(0, cy - ry), min(height, cy + ry + 1)):
        dy = (y - cy) / ry
        span = int(rx * max(0.0, 1.0 - dy * dy) ** 0.5)
        row = y * width * 3
        for x in range(max(0, cx - span), min(width, cx + span + 1)):
            idx = row + x * 3
            pixels[idx : idx + 3] = bytes(color)


def render_local_demo_png(prompt_payload: dict[str, Any], path: str | Path, *, size: str = DEFAULT_IMAGE_SIZE) -> str:
    width, height = _parse_size(size)
    pixels = bytearray([246, 243, 236] * width * height)
    variant = str(prompt_payload.get("image_id") or prompt_payload.get("variant_id") or "").lower()
    image_type = str(prompt_payload.get("image_type") or prompt_payload.get("content_task", {}).get("image_type", "")).lower()
    style = f"{variant} {image_type}"

    # Warm bakery counter background with a subtle product shadow.
    _fill_rect(pixels, width, height, 0, int(height * 0.68), width, height, (218, 203, 183))
    _fill_ellipse(pixels, width, height, width // 2, int(height * 0.72), int(width * 0.36), int(height * 0.08), (188, 170, 148))

    if "deconstruct" in style or "exploded" in style:
        pieces = [
            (0.50, 0.35, 0.26, 0.08, (186, 129, 69)),
            (0.50, 0.46, 0.30, 0.07, (229, 188, 120)),
            (0.42, 0.55, 0.18, 0.05, (116, 70, 43)),
            (0.58, 0.55, 0.18, 0.05, (139, 86, 48)),
            (0.50, 0.64, 0.27, 0.08, (201, 143, 78)),
        ]
    elif "cutaway" in style:
        pieces = [
            (0.48, 0.43, 0.33, 0.16, (190, 128, 66)),
            (0.52, 0.45, 0.25, 0.11, (238, 206, 145)),
            (0.54, 0.49, 0.20, 0.04, (126, 75, 44)),
        ]
    else:
        pieces = [
            (0.50, 0.50, 0.36, 0.18, (190, 128, 66)),
            (0.50, 0.52, 0.28, 0.11, (232, 194, 127)),
        ]
    for cx, cy, rx, ry, color in pieces:
        _fill_ellipse(pixels, width, height, int(width * cx), int(height * cy), int(width * rx), int(height * ry), color)

    for index in range(54):
        x = int(width * (0.22 + (index * 37 % 560) / 1000))
        y = int(height * (0.31 + (index * 53 % 350) / 1000))
        color = (95, 57, 34) if index % 3 == 0 else (242, 220, 164)
        _fill_ellipse(pixels, width, height, x, y, max(2, width // 140), max(2, height // 140), color)

    out = resolve_path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    _write_png(out, width, height, pixels)
    return str(out)


def image_config() -> dict[str, Any]:
    env = load_dotenv(".env")
    return {
        "provider": "openai",
        "api_key_present": bool(env.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY", "")),
        "base_url": env.get("OPENAI_BASE_URL") or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        "model": env.get("OPENAI_IMAGE_MODEL") or os.environ.get("OPENAI_IMAGE_MODEL", DEFAULT_IMAGE_MODEL),
        "size": env.get("OPENAI_IMAGE_SIZE") or os.environ.get("OPENAI_IMAGE_SIZE", DEFAULT_IMAGE_SIZE),
        "quality": env.get("OPENAI_IMAGE_QUALITY") or os.environ.get("OPENAI_IMAGE_QUALITY", DEFAULT_IMAGE_QUALITY),
        "timeout": int(env.get("OPENAI_TIMEOUT_SECONDS") or os.environ.get("OPENAI_TIMEOUT_SECONDS", "120") or "120"),
        "agent_api_live_image_allowed": env.get("AGENT_API_ALLOW_LIVE_IMAGE", "").lower() in {"1", "true", "yes"},
    }


def live_image_readiness(*, require_agent_api_allow: bool = False) -> dict[str, Any]:
    config = image_config()
    blockers: list[str] = []
    if not config["api_key_present"]:
        blockers.append("OPENAI_API_KEY is missing")
    if require_agent_api_allow and not config["agent_api_live_image_allowed"]:
        blockers.append("AGENT_API_ALLOW_LIVE_IMAGE is not enabled")
    return {
        "ready": not blockers,
        "blockers": blockers,
        **config,
    }


def build_prompt(payload: dict[str, Any]) -> str:
    prompt = payload.get("prompt_en") or payload.get("enhanced_prompt_en") or payload.get("prompt_zh") or payload.get("enhanced_prompt_zh") or ""
    negative = payload.get("negative_prompt", "")
    compliance = payload.get("compliance_rules", [])
    parts = [str(prompt).strip()]
    if negative:
        parts.append(f"Negative requirements: {negative}")
    if compliance:
        parts.append("Compliance requirements: " + "; ".join(str(item) for item in compliance))
    return "\n\n".join(part for part in parts if part)


def build_openai_image_request(prompt_payload: dict[str, Any], *, model: str = "gpt-image-2", size: str = "1024x1024", quality: str = "low", n: int = 1) -> dict[str, Any]:
    return {"model": model, "prompt": build_prompt(prompt_payload), "size": size, "quality": quality, "n": n}


def dry_run_openai_image(input_path: str | Path = DEFAULT_INPUT, out_dir: str | Path = DEFAULT_OUT_DIR, *, model: str = "gpt-image-2", size: str = "1024x1024", quality: str = "low", n: int = 1) -> dict[str, Any]:
    payload = read_json(input_path, {})
    request_payload = build_openai_image_request(payload, model=model, size=size, quality=quality, n=n)
    out = resolve_path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    metadata_path = out / f"bakery_image_{timestamp()}.json"
    report = {
        "mode": "dry_run",
        "provider": "openai",
        "model": model,
        "size": size,
        "quality": quality,
        "input": str(resolve_path(input_path)),
        "request_payload": request_payload,
        "status": "prepared",
        "image_paths": [],
        "metadata_path": str(metadata_path),
        "created_at": now_iso(),
    }
    write_json(metadata_path, report)
    return report


def iter_prompt_payloads(payload: dict[str, Any]) -> list[dict[str, Any]]:
    variants = payload.get("variants") or payload.get("image_prompts")
    if isinstance(variants, list) and variants:
        items: list[dict[str, Any]] = []
        for index, variant in enumerate(variants, start=1):
            if isinstance(variant, dict):
                item = {**payload, **variant}
                item.pop("variants", None)
                item.pop("image_prompts", None)
                item.setdefault("image_id", variant.get("variant_id") or variant.get("image_id") or f"image_{index:03d}")
                items.append(item)
        return items
    return [{**payload, "image_id": payload.get("image_id", "image_001")}]


def dry_run_openai_images(input_path: str | Path = DEFAULT_INPUT, out_dir: str | Path = DEFAULT_OUT_DIR, *, model: str = "gpt-image-2", size: str = "1024x1024", quality: str = "low", n: int = 1) -> dict[str, Any]:
    payload = read_json(input_path, {})
    out = resolve_path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    batch_id = f"image_batch_{timestamp()}"
    images: list[dict[str, Any]] = []
    for item in iter_prompt_payloads(payload):
        request_payload = build_openai_image_request(item, model=model, size=size, quality=quality, n=n)
        image_id = str(item.get("image_id", f"image_{len(images) + 1:03d}"))
        metadata_path = out / f"{batch_id}_{image_id}.json"
        image_report = {
            "image_id": image_id,
            "mode": "dry_run",
            "provider": "openai",
            "model": model,
            "size": size,
            "quality": quality,
            "input": str(resolve_path(input_path)),
            "request_payload": request_payload,
            "status": "prepared",
            "image_paths": [],
            "metadata_path": str(metadata_path),
            "created_at": now_iso(),
        }
        write_json(metadata_path, image_report)
        images.append(image_report)
    batch_path = out / f"{batch_id}.json"
    batch_report = {
        "mode": "dry_run",
        "status": "prepared",
        "asset_type": "image_batch",
        "provider": "openai",
        "input": str(resolve_path(input_path)),
        "metadata_path": str(batch_path),
        "images": images,
        "image_paths": [],
        "created_at": now_iso(),
    }
    write_json(batch_path, batch_report)
    return batch_report


def local_demo_images(input_path: str | Path = DEFAULT_INPUT, out_dir: str | Path = DEFAULT_OUT_DIR, *, size: str = "1024x1024", n: int = 1) -> dict[str, Any]:
    payload = read_json(input_path, {})
    out = resolve_path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    batch_id = f"local_demo_image_batch_{timestamp()}"
    images: list[dict[str, Any]] = []
    for item in iter_prompt_payloads(payload):
        image_id = str(item.get("image_id", f"image_{len(images) + 1:03d}"))
        image_paths: list[str] = []
        for index in range(1, max(1, n) + 1):
            suffix = f"_{index}" if n > 1 else ""
            image_path = out / f"{batch_id}_{image_id}{suffix}.png"
            image_paths.append(render_local_demo_png(item, image_path, size=size))
        metadata_path = out / f"{batch_id}_{image_id}.json"
        image_report = {
            "image_id": image_id,
            "mode": "local_demo",
            "provider": "local_demo",
            "model": "local_demo_png",
            "size": size,
            "quality": "demo",
            "input": str(resolve_path(input_path)),
            "request_payload": build_openai_image_request(item, model="local_demo_png", size=size, quality="demo", n=n),
            "status": "completed",
            "image_paths": image_paths,
            "metadata_path": str(metadata_path),
            "created_at": now_iso(),
        }
        write_json(metadata_path, image_report)
        images.append(image_report)
    batch_path = out / f"{batch_id}.json"
    batch_report = {
        "mode": "local_demo",
        "status": "completed",
        "asset_type": "image_batch",
        "provider": "local_demo",
        "input": str(resolve_path(input_path)),
        "metadata_path": str(batch_path),
        "images": images,
        "image_paths": [path for image in images for path in image.get("image_paths", [])],
        "created_at": now_iso(),
    }
    write_json(batch_path, batch_report)
    return batch_report


def call_openai_image_api(request_payload: dict[str, Any], *, api_key: str = "", base_url: str = "https://api.openai.com/v1", timeout: int = 120, dry_run: bool = True) -> dict[str, Any]:
    if dry_run:
        return {"status": "prepared", "mode": "dry_run", "request_payload": request_payload, "data": []}
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for live image generation")
    url = f"{base_url.rstrip('/')}/images/generations"
    request = urllib.request.Request(
        url,
        data=json.dumps(request_payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json; charset=utf-8", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"OpenAI image request failed HTTP {exc.code}: {body}") from exc
    data["mode"] = "live"
    data["status"] = "completed"
    return data


def save_image_result(response: dict[str, Any], out_dir: str | Path = DEFAULT_OUT_DIR, stem: str | None = None) -> list[str]:
    out = resolve_path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    name = stem or f"bakery_image_{timestamp()}"
    paths: list[str] = []
    for index, item in enumerate(response.get("data", []), start=1):
        b64_json = item.get("b64_json")
        if not b64_json:
            continue
        path = out / f"{name}_{index}.png"
        path.write_bytes(base64.b64decode(b64_json))
        paths.append(str(path))
    return paths


def generate_openai_image(input_path: str | Path = DEFAULT_INPUT, out_dir: str | Path = DEFAULT_OUT_DIR, *, live: bool = False, require_key: bool = False, n: int = 1, local_demo: bool = False) -> dict[str, Any]:
    config = image_config()
    env = load_dotenv(".env")
    api_key = env.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
    if require_key and not api_key:
        raise RuntimeError("OPENAI_API_KEY is required but missing")
    model = str(config["model"])
    size = str(config["size"])
    quality = str(config["quality"])
    base_url = str(config["base_url"])
    timeout = int(config["timeout"])
    payload = read_json(input_path, {})
    has_batch = bool(payload.get("variants") or payload.get("image_prompts"))
    if local_demo:
        return local_demo_images(input_path, out_dir, size=size, n=n)
    report = dry_run_openai_images(input_path, out_dir, model=model, size=size, quality=quality, n=n) if has_batch else dry_run_openai_image(input_path, out_dir, model=model, size=size, quality=quality, n=n)
    if live:
        if has_batch:
            live_images = []
            all_paths: list[str] = []
            for image_report in report["images"]:
                response = call_openai_image_api(image_report["request_payload"], api_key=api_key, base_url=base_url, timeout=timeout, dry_run=False)
                paths = save_image_result(response, out_dir, Path(image_report["metadata_path"]).stem)
                image_report.update({"mode": "live", "status": "completed", "response_id": response.get("id", ""), "image_paths": paths})
                write_json(image_report["metadata_path"], image_report)
                all_paths.extend(paths)
                live_images.append(image_report)
            report.update({"mode": "live", "status": "completed", "images": live_images, "image_paths": all_paths})
            write_json(report["metadata_path"], report)
        else:
            response = call_openai_image_api(report["request_payload"], api_key=api_key, base_url=base_url, timeout=timeout, dry_run=False)
            paths = save_image_result(response, out_dir, Path(report["metadata_path"]).stem)
            report.update({"mode": "live", "status": "completed", "response_id": response.get("id", ""), "image_paths": paths})
            write_json(report["metadata_path"], report)
    return report
