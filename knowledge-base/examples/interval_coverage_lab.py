"""Run from the repo root with Python 3.11+."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "examples" / "shift-coverage-review"))
from agent import coverage, EVIDENCE, SHIFT

if __name__ == "__main__":
    report = coverage(SHIFT["start"], SHIFT["end"], EVIDENCE["entries"])
    print("covered minutes:", int(report["covered_seconds"] / 60))
    print("gap minutes:", int(report["gap_seconds"] / 60))
    print("gap:", report["gaps"][0]["start"], report["gaps"][0]["end"])
