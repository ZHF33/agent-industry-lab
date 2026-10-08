#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services import db_service


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize the local SQLite operation database.")
    parser.add_argument("--db", default=str(db_service.DEFAULT_DB.relative_to(db_service.ROOT)))
    args = parser.parse_args()
    path = db_service.init_db(args.db)
    print(f"Initialized {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
