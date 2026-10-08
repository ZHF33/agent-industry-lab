#!/usr/bin/env python3
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
PROMPT_DIR = ROOT / "dify" / "prompts"
OUT = ROOT / "dify" / "prompts.export.json"


def main() -> int:
    payload = {}
    for path in sorted(PROMPT_DIR.glob("*.md")):
        payload[path.stem] = path.read_text(encoding="utf-8").strip()
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
