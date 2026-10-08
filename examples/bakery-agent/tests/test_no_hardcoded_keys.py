import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_no_hardcoded_api_keys():
    patterns = [re.compile(r"sk-[A-Za-z0-9_-]{20,}"), re.compile(r"(?i)(OPENAI_API_KEY|ANTHROPIC_API_KEY|DIFY_API_KEY)=\\S+")]
    for path in ROOT.rglob("*"):
        if any(part in {".venv", ".pytest_cache", "__pycache__"} for part in path.parts):
            continue
        if path.is_file() and path.suffix.lower() in {".py", ".md", ".json", ".yml", ".example"}:
            text = path.read_text(encoding="utf-8", errors="ignore")
            for pattern in patterns:
                assert not pattern.search(text), path

