#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "knowledge" / "raw"
OUT_DIR = ROOT / "knowledge" / "processed"

FIELD_ALIASES = {
    "name": ["产品名称", "名称", "商品名称", "品牌名称", "活动名称"],
    "product_type": ["产品类型", "品类", "类型", "商品类型"],
    "price": ["价格", "售价", "单价"],
    "ingredients": ["原料", "配料", "主要原料", "成分"],
    "selling_points": ["卖点", "亮点", "优势", "推荐理由"],
    "taste": ["口感", "风味", "味道"],
    "scenarios": ["适合场景", "场景", "使用场景", "消费场景"],
    "target_customers": ["目标用户", "目标人群", "适合人群", "用户画像"],
    "forbidden_claims": ["禁用表达", "禁用词", "禁止表达", "风险表达"],
    "notes": ["备注", "补充", "说明"],
    "positioning": ["品牌定位", "定位"],
    "tone": ["品牌语气", "语气", "调性"],
    "goal": ["目标", "活动目标", "营销目标"],
    "platforms": ["平台", "发布平台"],
}

TYPE_KEYWORDS = {
    "product": ["产品", "商品", "价格", "原料", "配料", "口感", "吐司", "面包", "蛋糕", "可颂", "贝果"],
    "brand": ["品牌", "定位", "门店", "故事", "调性", "口号"],
    "customer": ["用户", "顾客", "人群", "画像", "需求", "痛点"],
    "marketing": ["营销", "策略", "标题", "hook", "转化", "复购", "促销"],
    "competitor": ["竞品", "竞争", "对手", "附近", "价格带"],
    "platform": ["小红书", "抖音", "视频号", "平台规则", "发布规则"],
    "campaign": ["活动", "campaign", "投放", "曝光", "点赞", "转化", "ROI"],
}

TYPE_DIRS = {
    "product": "products",
    "brand": "brand",
    "customer": "customers",
    "marketing": "marketing",
    "competitor": "competitors",
    "platform": "platforms",
    "campaign": "campaigns",
    "unknown": "processed",
}

TAG_KEYWORDS = [
    "早餐",
    "下午茶",
    "儿童",
    "家庭",
    "上班族",
    "宝妈",
    "奶香",
    "低糖",
    "现烤",
    "新品",
    "节日",
    "复购",
    "小红书",
    "抖音",
    "吐司",
    "面包",
    "蛋糕",
    "可颂",
    "贝果",
]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore").strip()


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"\s+", "_", value)
    value = re.sub(r"[^\w\u4e00-\u9fff-]+", "", value)
    return value or "unnamed"


def split_list(value: str) -> list[str]:
    if not value:
        return []
    parts = re.split(r"[,，、;/；\n]+", value)
    return [part.strip(" -\t") for part in parts if part.strip(" -\t")]


def find_field(text: str, aliases: list[str]) -> str:
    for alias in aliases:
        pattern = rf"^\s*(?:[-*]\s*)?{re.escape(alias)}\s*[:：]\s*(.+?)\s*$"
        match = re.search(pattern, text, flags=re.MULTILINE)
        if match:
            return match.group(1).strip()
    return ""


def classify(text: str) -> tuple[str, str]:
    scores: dict[str, int] = {}
    lowered = text.lower()
    for record_type, keywords in TYPE_KEYWORDS.items():
        scores[record_type] = sum(1 for keyword in keywords if keyword.lower() in lowered)
    best_type = max(scores, key=scores.get)
    best_score = scores[best_type]
    if best_score == 0:
        return "unknown", "low"
    if best_score >= 3:
        return best_type, "high"
    return best_type, "medium"


def extract_tags(text: str, record_type: str) -> list[str]:
    tags = [tag for tag in TAG_KEYWORDS if tag.lower() in text.lower()]
    if record_type != "unknown":
        tags.insert(0, record_type)
    seen: set[str] = set()
    return [tag for tag in tags if not (tag in seen or seen.add(tag))]


def parse_price(value: str) -> int | float | str | None:
    if not value:
        return None
    match = re.search(r"\d+(?:\.\d+)?", value)
    if not match:
        return value
    number = float(match.group(0))
    return int(number) if number.is_integer() else number


def build_record(path: Path) -> dict[str, Any]:
    source = read_text(path)
    record_type, confidence = classify(source)
    fields: dict[str, Any] = {}
    todo: list[str] = []

    raw_values = {name: find_field(source, aliases) for name, aliases in FIELD_ALIASES.items()}
    name = raw_values["name"] or path.stem

    list_fields = {"ingredients", "selling_points", "scenarios", "target_customers", "forbidden_claims", "platforms"}
    for field_name, value in raw_values.items():
        if field_name in {"name", "price"}:
            continue
        fields[field_name] = split_list(value) if field_name in list_fields else value

    price = parse_price(raw_values["price"])
    if record_type == "product":
        required = ["product_type", "price", "ingredients", "selling_points", "taste", "scenarios", "target_customers"]
    elif record_type == "brand":
        required = ["positioning", "tone", "forbidden_claims"]
    elif record_type == "campaign":
        required = ["goal", "platforms"]
    else:
        required = ["notes"]

    for field_name in required:
        value = price if field_name == "price" else fields.get(field_name)
        if value in ("", [], None):
            todo.append(f"补充字段: {field_name}")

    if confidence == "low":
        todo.append("人工确认知识类型")

    record = {
        "id": f"{record_type}_{slugify(path.stem)}",
        "type": record_type,
        "name": name,
        "price": price,
        "currency": "CNY" if price is not None else "",
        "tags": extract_tags(source, record_type),
        "source_file": str(path.relative_to(ROOT)).replace("\\", "/"),
        "confidence": confidence,
        "fields": fields,
        "todo": todo,
        "raw_text": source if todo else "",
        "normalized_at": datetime.now(timezone.utc).isoformat(),
    }
    return record


def render_markdown(record: dict[str, Any]) -> str:
    fields = record["fields"]
    lines = [
        f"# {record['name']}",
        "",
        f"- ID: `{record['id']}`",
        f"- Type: `{record['type']}`",
        f"- Source: `{record['source_file']}`",
        f"- Confidence: `{record['confidence']}`",
        f"- Tags: {', '.join(record['tags']) if record['tags'] else 'TODO'}",
        "",
        "## Structured Fields",
        "",
    ]
    if record["price"] is not None:
        lines.append(f"- price: {record['price']} {record['currency']}".strip())
    for key, value in fields.items():
        if value in ("", [], None):
            continue
        if isinstance(value, list):
            lines.append(f"- {key}: {', '.join(value)}")
        else:
            lines.append(f"- {key}: {value}")
    lines.extend(["", "## TODO", ""])
    lines.extend([f"- {item}" for item in record["todo"]] or ["- None"])
    if record.get("raw_text"):
        lines.extend(["", "## Raw Text", "", record["raw_text"]])
    lines.append("")
    return "\n".join(lines)


def write_record(record: dict[str, Any], source_path: Path) -> None:
    out_base = OUT_DIR / source_path.stem
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_base.with_suffix(".standard.md").write_text(render_markdown(record), encoding="utf-8")
    out_base.with_suffix(".json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    curated_dir_name = TYPE_DIRS.get(record["type"], "processed")
    if curated_dir_name != "processed":
        curated_dir = ROOT / "knowledge" / curated_dir_name
        curated_dir.mkdir(parents=True, exist_ok=True)
        curated_path = curated_dir / f"{source_path.stem}.json"
        curated_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    files = sorted(path for path in RAW_DIR.iterdir() if path.suffix.lower() in {".txt", ".md"})
    if not files:
        print("No .txt or .md files found in knowledge/raw.")
        return 0

    for path in files:
        record = build_record(path)
        write_record(record, path)
        print(f"Wrote knowledge/processed/{path.stem}.standard.md and knowledge/processed/{path.stem}.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
