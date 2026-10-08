from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from .common import ROOT, resolve_path


PRODUCT_EXAMPLE_HEADING = "## Product Fact Examples"
PRODUCT_ALIAS_TERMS = {
    "beef ciabatta": ("beef ciabatta", "牛肉恰巴塔", "牛肉 ciabatta"),
    "butter croissant": ("butter croissant", "黄油可颂", "黄油牛角包"),
    "sourdough loaf": ("sourdough loaf", "酸面包", "酸种面包"),
    "blueberry muffin": ("blueberry muffin", "蓝莓马芬", "蓝莓麦芬"),
    "cinnamon roll": ("cinnamon roll", "肉桂卷"),
}


def _run_script(args: list[str]) -> None:
    subprocess.run([sys.executable, *args], cwd=ROOT, check=True)


def normalize_raw_knowledge() -> None:
    _run_script(["scripts/normalize_knowledge.py"])


def build_knowledge_index() -> None:
    _run_script(["scripts/build_knowledge_index.py"])


def build_agent_context(query: str = "bakery products", out: str = "knowledge/processed/agent_context.md") -> None:
    _run_script(["scripts/build_agent_context.py", "--query", query, "--out", out])


def classify_knowledge_doc(path: str | Path) -> str:
    text = resolve_path(path).read_text(encoding="utf-8", errors="ignore").lower()
    if "价格" in text or "原料" in text or "产品" in text:
        return "product"
    if "品牌" in text:
        return "brand"
    if "小红书" in text or "抖音" in text:
        return "platform"
    if "活动" in text or "campaign" in text:
        return "campaign"
    return "unknown"


def export_dify_ready_context(query: str = "bakery products") -> Path:
    out = ROOT / "knowledge" / "processed" / "agent_context.dify.md"
    build_agent_context(query=query, out=str(out))
    return out


def build_task_knowledge_context(
    task: dict[str, Any],
    context_path: str | Path = "knowledge/processed/bakery_agent_context.md",
    max_chars: int = 4800,
) -> str:
    path = resolve_path(context_path)
    if not path.exists():
        return ""
    source = path.read_text(encoding="utf-8")
    filtered = filter_task_knowledge_context(source, task)
    return truncate_context(filtered, max_chars)


def filter_task_knowledge_context(source: str, task: dict[str, Any]) -> str:
    sections = split_markdown_h2_sections(source)
    kept: list[str] = []
    product_examples = ""

    for heading, body in sections:
        section = body if not heading else f"{heading}\n{body}".rstrip()
        if heading == PRODUCT_EXAMPLE_HEADING:
            product_examples = body
            continue
        if section.strip():
            kept.append(section.strip())

    kept.insert(1 if kept else 0, build_current_task_section(task))
    matched_examples = select_product_examples(product_examples, task)
    if matched_examples:
        kept.insert(find_insert_index_after_supported_sections(kept), f"{PRODUCT_EXAMPLE_HEADING}\n\n{matched_examples}".strip())
    else:
        kept.insert(
            find_insert_index_after_supported_sections(kept),
            "## Product Fact Examples\n\nNo matching product example was found. Use the current content_task_json as source of truth and do not borrow facts from other products.",
        )

    return "\n\n".join(kept).strip() + "\n"


def build_current_task_section(task: dict[str, Any]) -> str:
    fields = [
        "product_name",
        "natural_request",
        "content_type",
        "image_type",
        "image_style",
        "visual_intent",
        "platforms",
        "campaign_goal",
        "audience",
        "constraints",
    ]
    lines = ["## Current Task"]
    for field in fields:
        value = task.get(field)
        if value:
            lines.append(f"- {field}: {value}")
    lines.append("- Source of truth: use the current task above before any reusable examples.")
    return "\n".join(lines)


def split_markdown_h2_sections(source: str) -> list[tuple[str, str]]:
    lines = source.splitlines()
    sections: list[tuple[str, list[str]]] = [("", [])]
    for line in lines:
        if line.startswith("## "):
            sections.append((line.strip(), []))
            continue
        sections[-1][1].append(line)
    return [(heading, "\n".join(body).strip()) for heading, body in sections]


def select_product_examples(product_examples: str, task: dict[str, Any]) -> str:
    if not product_examples.strip():
        return ""
    query = build_product_match_query(task)
    selected: list[str] = []
    for line in product_examples.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue
        if product_example_matches(stripped, query):
            selected.append(stripped)
    return "\n".join(selected)


def build_product_match_query(task: dict[str, Any]) -> str:
    values = [
        task.get("product_name", ""),
        task.get("natural_request", ""),
    ]
    return " ".join(str(value).lower() for value in values if value)


def product_example_matches(example_line: str, query: str) -> bool:
    normalized_example = example_line.lower()
    for canonical, terms in PRODUCT_ALIAS_TERMS.items():
        if canonical in normalized_example and any(term.lower() in query for term in terms):
            return True
    title = normalized_example.removeprefix("- ").split(":", 1)[0].strip()
    return bool(title and title in query)


def find_insert_index_after_supported_sections(sections: list[str]) -> int:
    for index, section in enumerate(sections):
        if section.startswith("## Supported Image Types"):
            return index + 1
    return len(sections)


def truncate_context(context: str, max_chars: int) -> str:
    if not max_chars or len(context) <= max_chars:
        return context
    marker = "\n\n## Context Truncated\n"
    return context[: max(0, max_chars - len(marker))].rstrip() + marker
