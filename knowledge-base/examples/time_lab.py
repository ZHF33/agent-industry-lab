"""Timezone and snapshot lesson; standard library only."""
from datetime import datetime


def parse(value):
    moment = datetime.fromisoformat(value)
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError("Timezone is required")
    return moment


if __name__ == "__main__":
    eta = parse("2026-10-12T12:00:00+00:00")
    local = parse("2026-10-12T08:00:00-04:00")
    snapshot = parse("2026-10-12T13:00:00+00:00")
    print("same_instant", eta == local)
    print("overdue_minutes", int(max(0, (snapshot - eta).total_seconds()) // 60))
    try:
        parse("2026-10-12T12:00:00")
    except ValueError:
        print("missing_timezone rejected")
