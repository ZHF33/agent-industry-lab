#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services import image_prompt_service


def resolve_workspace_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def load_dify_outputs(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("data", {}).get("outputs", {})


def main() -> int:
    parser = argparse.ArgumentParser(description="Enhance Dify image prompt with local image/social-card skill rules.")
    parser.add_argument("--input", default="runs/bakery_latest_output.json")
    parser.add_argument("--out-json", default="runs/bakery_latest_image_prompt.json")
    parser.add_argument("--out-md", default="runs/bakery_latest_image_prompt.md")
    args = parser.parse_args()

    outputs = load_dify_outputs(resolve_workspace_path(args.input))
    enhanced = image_prompt_service.build_enhanced_prompt(outputs, source=args.input)

    out_json = resolve_workspace_path(args.out_json)
    out_md = resolve_workspace_path(args.out_md)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(enhanced, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_md.write_text(image_prompt_service.render_markdown(enhanced), encoding="utf-8")
    print(json.dumps({"out_json": str(out_json), "out_md": str(out_md)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
