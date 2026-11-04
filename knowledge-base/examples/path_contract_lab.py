"""Lexical path contract illustration only; never opens attachment paths."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "examples" / "attachment-intake-review"))
from agent import path_issues

if __name__ == "__main__":
    for name in ["docs/spec.pdf", "../outside.csv", "C:/outside.pdf", "a//x.pdf", "%2e%2e/x.pdf", "CON.pdf"]:
        print(name, "=>", path_issues(name))
