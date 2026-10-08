#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_DIR = ROOT / "knowledge"
PROCESSED_DIR = KNOWLEDGE_DIR / "processed"
INDEX_PATH = PROCESSED_DIR / "knowledge_index.json"
DATA_INDEX_PATH = ROOT / "data" / "knowledge_index.json"

RECORD_DIRS = [
    "processed",
    "products",
    "brand",
    "customers",
    "marketing",
    "competitors",
    "platforms",
    "campaigns",
]


def load_record(path: Path) -> dict[str, Any] | None:
    if path.name == "knowledge_index.json":
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict) or "id" not in data or "type" not in data:
        return None
    data["_path"] = str(path.relative_to(ROOT)).replace("\\", "/")
    return data


def main() -> int:
    records_by_id: dict[str, dict[str, Any]] = {}
    for dirname in RECORD_DIRS:
        directory = KNOWLEDGE_DIR / dirname
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.json")):
            record = load_record(path)
            if record:
                records_by_id[record["id"]] = record

    records = sorted(records_by_id.values(), key=lambda item: (item["type"], item["name"], item["id"]))
    by_type: dict[str, list[str]] = defaultdict(list)
    tag_counter: Counter[str] = Counter()
    todo_records: list[dict[str, Any]] = []

    for record in records:
        by_type[record["type"]].append(record["id"])
        tag_counter.update(record.get("tags", []))
        if record.get("todo"):
            todo_records.append(
                {
                    "id": record["id"],
                    "name": record["name"],
                    "type": record["type"],
                    "todo": record["todo"],
                    "path": record["_path"],
                }
            )

    index = {
        "version": "1.1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "record_count": len(records),
        "by_type": {key: sorted(value) for key, value in sorted(by_type.items())},
        "top_tags": [{"tag": tag, "count": count} for tag, count in tag_counter.most_common(30)],
        "records": [
            {
                "id": record["id"],
                "type": record["type"],
                "name": record["name"],
                "tags": record.get("tags", []),
                "confidence": record.get("confidence", "unknown"),
                "path": record["_path"],
                "source_file": record.get("source_file", ""),
            }
            for record in records
        ],
        "todo_records": todo_records,
    }
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    DATA_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_INDEX_PATH.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {INDEX_PATH.relative_to(ROOT)} with {len(records)} records.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
