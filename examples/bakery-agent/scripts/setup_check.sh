#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="${0%/*}"
if [ "$SCRIPT_DIR" = "$0" ]; then
  SCRIPT_DIR="."
fi
cd "$SCRIPT_DIR/.."

PYTHON_BIN="python"
if [ -x ".venv/Scripts/python.exe" ]; then
  PYTHON_BIN=".venv/Scripts/python.exe"
elif [ -x ".venv/bin/python" ]; then
  PYTHON_BIN=".venv/bin/python"
fi

"$PYTHON_BIN" scripts/validate_project.py

if command -v docker >/dev/null 2>&1; then
  if docker info >/dev/null 2>&1 && docker compose config >/dev/null 2>&1; then
    echo "docker compose config passed."
  else
    echo "docker found but daemon/compose is not accessible in this shell; skipped docker compose config."
  fi
else
  echo "docker not found; skipped docker compose config."
fi

echo "setup check passed."
