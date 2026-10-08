#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_DIR = ROOT / "knowledge"
DEFAULT_OUT = KNOWLEDGE_DIR / "processed" / "agent_context.md"
RECORD_DIRS = ["products", "brand", "customers", "marketing", "competitors", "platforms", "campaigns"]


def load_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for dirname in RECORD_DIRS:
        for path in sorted((KNOWLEDGE_DIR / dirname).glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            data["_path"] = str(path.relative_to(ROOT)).replace("\\", "/")
            records.append(data)
    return records


def matches(record: dict[str, Any], query: str, record_type: str) -> bool:
    if record_type and record.get("type") != record_type:
        return False
    if not query:
        return True
    haystack = json.dumps(record, ensure_ascii=False).lower()
    return query.lower() in haystack


def render_value(value: Any) -> str:
    if value in ("", None, [], {}):
        return ""
    if isinstance(value, list):
        return "\n".join(f"  - {render_value(item).strip()}" for item in value if render_value(item).strip())
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def render_record(record: dict[str, Any]) -> list[str]:
    lines = [
        f"## {record.get('name', record.get('id', 'Unknown'))}",
        "",
        f"- id: `{record.get('id', '')}`",
        f"- type: `{record.get('type', '')}`",
        f"- confidence: `{record.get('confidence', '')}`",
        f"- source_file: `{record.get('source_file', '')}`",
        f"- record_path: `{record.get('_path', '')}`",
        f"- tags: {', '.join(record.get('tags', []))}",
        "",
    ]
    if record.get("price") is not None:
        lines.append(f"- price: {record.get('price')} {record.get('currency', '')}".strip())
        lines.append("")

    fields = record.get("fields", {})
    for key, value in fields.items():
        rendered = render_value(value)
        if not rendered:
            continue
        lines.append(f"### {key}")
        lines.append(rendered)
        lines.append("")

    sources = record.get("sources", [])
    if sources:
        lines.append("### sources")
        lines.extend(f"- {source}" for source in sources)
        lines.append("")

    todo = record.get("todo", [])
    if todo:
        lines.append("### todo")
        lines.extend(f"- {item}" for item in todo)
        lines.append("")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a compact Markdown context file from knowledge JSON records.")
    parser.add_argument("--query", default="", help="Only include records containing this text.")
    parser.add_argument("--type", default="", choices=["", "product", "brand", "customer", "marketing", "competitor", "platform", "campaign"])
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output Markdown path.")
    parser.add_argument("--max-chars", type=int, default=0, help="Truncate output to this many characters.")
    args = parser.parse_args()

    records = [record for record in load_records() if matches(record, args.query, args.type)]
    records.sort(key=lambda item: (item.get("type", ""), item.get("name", ""), item.get("id", "")))

    lines = [
        "# Agent Knowledge Context",
        "",
        f"- query: {args.query or 'all'}",
        f"- type: {args.type or 'all'}",
        f"- record_count: {len(records)}",
        "",
        "This file is generated from local structured knowledge records. It is safe to paste into Dify workflow inputs for testing.",
        "",
    ]
    for record in records:
        lines.extend(render_record(record))
        if args.max_chars and len("\n".join(lines)) >= args.max_chars:
            lines.extend(["", "## Context Truncated", "", f"Output was truncated to fit {args.max_chars} characters."])
            break

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    output = "\n".join(lines).strip() + "\n"
    if args.max_chars and len(output) > args.max_chars:
        output = output[: args.max_chars - 80].rstrip() + "\n\n## Context Truncated\nOutput was truncated.\n"
    out_path.write_text(output, encoding="utf-8")
    print(f"Wrote {out_path.relative_to(ROOT)} with {len(records)} records.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
