"""Read-only synthetic order export evidence. No remote page fetching."""
import json
import os
import urllib.request
from datetime import datetime, timezone

EXPORT = {"source": "export-demo-01", "export_id": "EXPORT-DEMO-A",
          "snapshot": "SNAP-A", "expected_unique": 4, "first_cursor": "P0"}
PAGES = {"source": "pages-demo-01", "export_id": "EXPORT-DEMO-A",
         "observed_at": "2026-11-05T12:00:00Z", "entries": [
             {"source": "page-A", "cursor": "P0", "next_cursor": "P1", "snapshot": "SNAP-A",
              "ids": ["ROW-1", "ROW-2"]},
             {"source": "page-B", "cursor": "P1", "next_cursor": "P2", "snapshot": "SNAP-A",
              "ids": ["ROW-2", "ROW-3"]}]}
POLICY = {"source": "export-policy-demo-01", "max_pages": 10, "max_age_seconds": 60}


def instant(value):
    if not isinstance(value, str):
        raise ValueError("Timestamp text required")
    parsed = datetime.fromisoformat(value)
    if parsed.utcoffset() is None:
        raise ValueError("Explicit offset required")
    return parsed.astimezone(timezone.utc)


def text(value):
    return isinstance(value, str) and 0 < len(value) <= 100 and bool(value.strip())


def inspect_pages(export, entries, max_pages=10):
    if type(max_pages) is not int or not 1 <= max_pages <= 20:
        raise ValueError("Invalid page budget")
    if type(export["expected_unique"]) is not int or export["expected_unique"] < 0:
        raise ValueError("Expected count must be nonnegative integer")
    if not text(export["snapshot"]) or not text(export["first_cursor"]):
        raise ValueError("Snapshot and initial cursor required")
    if not isinstance(entries, list) or len(entries) > 20:
        raise ValueError("At most 20 evidence pages")
    pages, sources = {}, set()
    for page in entries:
        if not isinstance(page, dict) or set(page) != {"source", "cursor", "next_cursor", "snapshot", "ids"}:
            raise ValueError("Invalid page fields")
        if any(not text(page[key]) for key in ("source", "cursor", "snapshot")):
            raise ValueError("Page identity required")
        if page["next_cursor"] is not None and not text(page["next_cursor"]):
            raise ValueError("Explicit next cursor or null required")
        if (not isinstance(page["ids"], list) or len(page["ids"]) > 100
                or any(not text(value) for value in page["ids"])):
            raise ValueError("At most 100 text IDs per page")
        if page["cursor"] in pages or page["source"] in sources:
            raise ValueError("Ambiguous duplicate page identity")
        pages[page["cursor"]] = page
        sources.add(page["source"])

    cursor = export["first_cursor"]
    visited, seen, duplicates, trace, reasons = set(), set(), set(), [], []
    terminal = False
    total_rows = 0
    while True:
        if cursor in visited:
            reasons.append("cursor_cycle")
            break
        if len(visited) >= max_pages:
            reasons.append("page_budget_exhausted")
            break
        page = pages.get(cursor)
        if page is None:
            reasons.append("missing_page")
            break
        visited.add(cursor)
        trace.append({"cursor": cursor, "source": page["source"]})
        if page["snapshot"] != export["snapshot"]:
            reasons.append("snapshot_mismatch")
            break
        for identity in page["ids"]:
            if identity in seen:
                duplicates.add(identity)
            seen.add(identity)
            total_rows += 1
        if page["next_cursor"] is None:
            terminal = True
            break
        cursor = page["next_cursor"]
    if duplicates:
        reasons.append("duplicate_records")
    if len(seen) != export["expected_unique"]:
        reasons.append("unique_count_mismatch")
    unused = sorted(set(pages) - visited)
    if unused:
        reasons.append("unlinked_evidence_pages")
    return {"terminal_seen": terminal, "page_trace": trace, "row_count": total_rows,
            "unique_count": len(seen), "duplicate_ids": sorted(duplicates),
            "unused_cursors": unused, "reasons": reasons,
            "blocked_cursor": None if terminal else cursor}


def assess(export, evidence, as_of):
    if export["export_id"] != evidence["export_id"]:
        raise ValueError("Export identity mismatch")
    observed, reference = instant(evidence["observed_at"]), instant(as_of)
    if observed > reference:
        raise ValueError("Future evidence")
    result = inspect_pages(export, evidence["entries"], POLICY["max_pages"])
    if (reference - observed).total_seconds() > POLICY["max_age_seconds"]:
        result["reasons"].append("stale_evidence")
    return {"source": "export-assessment-demo-01", **result,
            "inputs": [export["source"], evidence["source"], POLICY["source"]],
            "status": "human_review_required", "actions_executed": False,
            "live_business_completeness_verified": False}


def tools():
    descriptions = {"lookup_export": "Read scoped synthetic export snapshot and expected unique count",
                    "lookup_pages": "Read collected synthetic page metadata without fetching pages",
                    "assess_export": "Trace cursor chain and report duplicates, gaps, terminal and snapshot consistency"}
    return [{"type": "function", "function": {"name": name, "description": description,
             "parameters": {"type": "object", "properties": {"export_id": {"type": "string"}},
                            "required": ["export_id"], "additionalProperties": False}}}
            for name, description in descriptions.items()]


def execute(name, arguments, export_id, as_of):
    if (name not in {"lookup_export", "lookup_pages", "assess_export"}
            or arguments != {"export_id": export_id} or export_id != EXPORT["export_id"]):
        raise ValueError("Invalid tool or export scope")
    if name == "lookup_export":
        return [EXPORT, POLICY]
    if name == "lookup_pages":
        return [PAGES]
    return [assess(EXPORT, PAGES, as_of)]


def chat(messages):
    payload = {"model": os.environ.get("OLLAMA_MODEL", "qwen3:4b"), "messages": messages,
               "tools": tools(), "stream": False, "think": True,
               "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 2500}}
    request = urllib.request.Request("http://127.0.0.1:11434/api/chat", data=json.dumps(payload).encode(),
                                    headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)["message"]
