import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_agent_context_for_bakery():
    out = ROOT / "knowledge" / "processed" / "pytest_agent_context.md"
    if out.exists():
        out.unlink()
    try:
        subprocess.run(
            [sys.executable, "scripts/build_agent_context.py", "--query", "bakery products", "--out", str(out)],
            cwd=ROOT,
            check=True,
        )
        text = out.read_text(encoding="utf-8")
        assert "Agent Knowledge Context" in text
        assert "bakery products" in text
        assert "record_count:" in text
    finally:
        if out.exists():
            out.unlink()
