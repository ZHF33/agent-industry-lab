"""Run manually from the repository root. Uses synthetic page evidence."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "examples" / "export-page-review"))
from agent import inspect_pages, EXPORT, PAGES

if __name__ == "__main__":
    result = inspect_pages(EXPORT, PAGES["entries"])
    print("rows:", result["row_count"])
    print("unique:", result["unique_count"])
    print("duplicates:", result["duplicate_ids"])
    print("blocked:", result["blocked_cursor"])
    print("terminal:", result["terminal_seen"])
