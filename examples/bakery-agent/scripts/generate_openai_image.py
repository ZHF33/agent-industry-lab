#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services import approval_service, image_service
from services.common import ROOT


def find_latest_approval_package() -> Path | None:
    queue = ROOT / "runs" / "approval_queue"
    if not queue.exists():
        return None
    packages = []
    for path in queue.glob("run_*"):
        if not path.is_dir():
            continue
        metadata = approval_service.load_approval_package(path)["metadata"]
        status = metadata.get("approval_status", metadata.get("status", ""))
        if status == "approved":
            packages.append(path)
    return max(packages, key=lambda path: path.stat().st_mtime) if packages else None


def require_approved_package(package_dir: str | Path) -> None:
    metadata = approval_service.load_approval_package(package_dir)["metadata"]
    status = metadata.get("approval_status", metadata.get("status", ""))
    if status != "approved":
        raise RuntimeError(
            "generate_openai_image.py can only backfill approved packages. "
            "Use scripts/generate_approved_images.py for the V2 approval-gated path."
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate an OpenAI GPT Image asset from the enhanced image prompt.")
    parser.add_argument("--input", default=image_service.DEFAULT_INPUT)
    parser.add_argument("--out-dir", default=image_service.DEFAULT_OUT_DIR)
    parser.add_argument("--live", action="store_true", help="Actually call OpenAI Images API. Default is dry-run.")
    parser.add_argument("--local-demo", action="store_true", help="Generate local demo PNG images without calling a paid provider.")
    parser.add_argument("--require-key", action="store_true", help="Fail if OPENAI_API_KEY is missing.")
    parser.add_argument("--approval-package", default="", help="Approval package directory to update after generation.")
    parser.add_argument("--latest-approval-package", action="store_true", help="Update the latest approved package.")
    parser.add_argument("--n", type=int, default=1)
    args = parser.parse_args()

    report = image_service.generate_openai_image(args.input, args.out_dir, live=args.live, require_key=args.require_key, n=args.n, local_demo=args.local_demo)

    package_dir = args.approval_package
    if not package_dir and args.latest_approval_package:
        latest = find_latest_approval_package()
        package_dir = str(latest) if latest else ""
    if package_dir:
        require_approved_package(package_dir)
        approval_service.backfill_asset_result(package_dir, "image", report)
        report["approval_package"] = package_dir

    print(json.dumps({k: report.get(k) for k in ["mode", "status", "model", "metadata_path", "image_paths", "approval_package"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
