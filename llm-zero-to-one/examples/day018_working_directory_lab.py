"""Print path context without opening the supplied path."""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("provide exactly one path")
print("cwd=" + str(Path.cwd()))
print("script_dir=" + str(Path(__file__).resolve().parent))
print("input=" + str(Path(sys.argv[1]).resolve()))
