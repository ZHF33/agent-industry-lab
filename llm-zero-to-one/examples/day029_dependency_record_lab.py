"""Inspect declared direct pins; optionally compare installed distribution versions."""
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import sys


def declarations():
    path = Path(__file__).resolve().parents[2] / "examples/material-kitting-review/requirements.txt"
    return [line.split("==", 1) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


if __name__ == "__main__":
    pins = declarations()
    print(f"direct declarations={len(pins)}")
    for name, expected in pins:
        print(f"declared {name}=={expected}")
        if sys.argv[1:] == ["--installed"]:
            try:
                actual = version(name)
            except PackageNotFoundError:
                print("installed missing")
            else:
                print(f"installed {actual} matches={actual == expected}")
