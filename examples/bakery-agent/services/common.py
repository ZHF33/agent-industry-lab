from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def resolve_path(value: str | Path) -> Path:
    if isinstance(value, str) and value.startswith("/workspace/"):
        return ROOT / value.removeprefix("/workspace/")
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def display_path(path: str | Path) -> str:
    resolved = Path(path)
    return str(resolved.relative_to(ROOT)) if resolved.is_absolute() and resolved.is_relative_to(ROOT) else str(resolved)


def read_json(path: str | Path, default: Any = None) -> Any:
    resolved = resolve_path(path)
    if not resolved.exists():
        return default
    return json.loads(resolved.read_text(encoding="utf-8"))


def write_json(path: str | Path, data: Any) -> Path:
    resolved = resolve_path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    last_error: PermissionError | None = None
    for attempt in range(5):
        try:
            if resolved.exists():
                with resolved.open("r+", encoding="utf-8") as handle:
                    handle.seek(0)
                    handle.write(text)
                    handle.truncate()
            else:
                resolved.write_text(text, encoding="utf-8")
            return resolved
        except PermissionError as exc:
            last_error = exc
            time.sleep(0.1 * (attempt + 1))
    if last_error:
        raise last_error
    return resolved


def parse_json_text(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    if not isinstance(value, str):
        return value
    text = value.strip()
    if text.startswith("```"):
        text = text.strip("`").replace("json\n", "", 1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return value


def load_dotenv(path: str | Path = ".env") -> dict[str, str]:
    resolved = resolve_path(path)
    values: dict[str, str] = {}
    if not resolved.exists():
        return values
    for line in resolved.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip().lstrip("\ufeff")] = value.strip()
    return values
