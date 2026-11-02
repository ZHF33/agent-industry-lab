"""Synthetic manifest inspection only; never accesses attachment paths or bytes."""
import json
import os
import re
import urllib.request
from pathlib import PurePosixPath, PureWindowsPath
from datetime import datetime, timezone

BATCHES = {"BATCH-DEMO-01": {
    "batch": {"source": "batch-demo-01", "batch_id": "BATCH-DEMO-01", "supplier": "DEMO-SUPPLIER",
              "observed_at": "2026-11-02T12:00:00+00:00"},
    "manifest": {"source": "manifest-demo-01", "batch_id": "BATCH-DEMO-01",
                 "observed_at": "2026-11-02T12:00:00+00:00", "entries": [
                     {"entry_id": "ATT-1", "path": "docs/spec.pdf", "declared_bytes": 2048, "declared_type": "application/pdf"},
                     {"entry_id": "ATT-2", "path": "../outside.csv", "declared_bytes": 100, "declared_type": "text/csv"},
                     {"entry_id": "ATT-3", "path": "data/table.csv", "declared_bytes": 6000000, "declared_type": "application/pdf"}]}
}}
POLICY = {"source": "intake-policy-demo-01", "max_file_bytes": 5000000, "max_total_bytes": 10000000,
          "max_age_seconds": 60, "allowed_types": {".pdf": "application/pdf", ".csv": "text/csv"},
          "scope": "Narrow ASCII relative-path metadata contract; no file inspection or import permission."}


def instant(value):
    if not isinstance(value, str): raise ValueError("Timestamp text required")
    result = datetime.fromisoformat(value)
    if result.tzinfo is None or result.utcoffset() is None: raise ValueError("Timezone required")
    return result.astimezone(timezone.utc)


def path_issues(value):
    """Deliberately narrow wire contract, not a filesystem containment guarantee."""
    if not isinstance(value, str) or not 1 <= len(value) <= 240: return ["invalid_path_text"]
    if PurePosixPath(value).is_absolute() or PureWindowsPath(value).drive or value.startswith("\\"):
        return ["absolute_or_drive_path"]
    # Reject encoded/ambiguous spelling, not normalize it into an accepted name.
    if "\\" in value or ":" in value or "%" in value: return ["ambiguous_path_syntax"]
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts): return ["empty_or_dot_segment"]
    reserved = {"CON", "PRN", "AUX", "NUL"} | {f"COM{i}" for i in range(1, 10)} | {f"LPT{i}" for i in range(1, 10)}
    for part in parts:
        if (not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", part)
                or part.endswith((".", " ")) or part.split(".")[0].upper() in reserved):
            return ["unsupported_segment"]
    return []


def assess(evidence, as_of):
    batch, manifest = evidence["batch"], evidence["manifest"]
    if batch["batch_id"] != manifest["batch_id"]: raise ValueError("Batch mismatch")
    reference = instant(as_of); observed = [instant(x["observed_at"]) for x in (batch, manifest)]
    if any(t > reference for t in observed): raise ValueError("Future evidence")
    entries = manifest["entries"]
    if not isinstance(entries, list) or not 1 <= len(entries) <= 100: raise ValueError("Need 1–100 entries")
    seen_ids, seen_paths = set(), set(); total = 0; reports = []
    for item in entries:
        if not isinstance(item, dict) or set(item) != {"entry_id", "path", "declared_bytes", "declared_type"}:
            raise ValueError("Invalid manifest fields")
        identity, path, size, media = (item[k] for k in ("entry_id", "path", "declared_bytes", "declared_type"))
        if not isinstance(identity, str) or not re.fullmatch(r"[A-Za-z0-9-]{1,80}", identity) or identity in seen_ids:
            raise ValueError("Unique entry ID required")
        if type(size) is not int or size < 0 or not isinstance(media, str) or len(media) > 120:
            raise ValueError("Nonnegative integer size and short type required")
        seen_ids.add(identity); total += size
        reasons = path_issues(path)
        if not reasons:
            folded = path.casefold()
            if folded in seen_paths: reasons.append("duplicate_path")
            seen_paths.add(folded)
            expected = POLICY["allowed_types"].get(PurePosixPath(path).suffix.lower())
            if expected is None: reasons.append("extension_not_allowed")
            elif media != expected: reasons.append("declared_type_mismatch")
        if size > POLICY["max_file_bytes"]: reasons.append("declared_size_exceeds_limit")
        reports.append({"entry_id": identity, "path": path, "reasons": reasons,
                        "metadata_status": "exception" if reasons else "no_metadata_exception",
                        "content_verified": False, "malware_status": "unknown"})
    reasons = []
    if any((reference-t).total_seconds() > POLICY["max_age_seconds"] for t in observed): reasons.append("stale_snapshot")
    if total > POLICY["max_total_bytes"]: reasons.append("declared_batch_size_exceeds_limit")
    count = sum(bool(r["reasons"]) for r in reports)
    if count: reasons.append("entry_metadata_exceptions")
    return {"source": "intake-assessment-demo-01", "inputs": [batch["source"], manifest["source"], POLICY["source"]],
            "status": "manual_isolation_review" if reasons else "manual_content_review",
            "reasons": reasons, "exception_entry_count": count, "declared_total_bytes": total,
            "entries": reports, "import_authorized": False, "files_opened": False, "actions_executed": False}


def tools():
    descriptions = {"lookup_batch": "Read scoped synthetic batch identity and intake policy",
                    "lookup_manifest": "Read untrusted attachment path/size/type declarations; never open files",
                    "assess_intake": "Inspect metadata contract and return exceptions; content and malware status remain unknown"}
    return [{"type": "function", "function": {"name": name, "description": description,
             "parameters": {"type": "object", "properties": {"batch_id": {"type": "string"}},
                            "required": ["batch_id"], "additionalProperties": False}}} for name, description in descriptions.items()]


def execute(name, arguments, batch_id, as_of):
    if (name not in {t["function"]["name"] for t in tools()} or not isinstance(arguments, dict)
            or set(arguments) != {"batch_id"} or arguments["batch_id"] != batch_id):
        raise ValueError("Invalid tool or batch scope")
    data = BATCHES.get(batch_id)
    if data is None: raise ValueError("Unknown synthetic batch")
    if name == "lookup_batch": return [data["batch"], POLICY]
    if name == "lookup_manifest": return [data["manifest"]]
    return [assess(data, as_of)]


def chat(messages):
    payload = {"model": os.environ.get("OLLAMA_MODEL", "qwen3:4b"), "messages": messages,
               "tools": tools(), "stream": False, "think": True,
               "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 2500}}
    request = urllib.request.Request("http://127.0.0.1:11434/api/chat", data=json.dumps(payload).encode(),
                                    headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=120) as response: return json.load(response)["message"]
