from datetime import datetime


if __name__ == "__main__":
    snapshot = datetime.fromisoformat("2026-10-15T12:03:00+00:00")
    latest = datetime.fromisoformat("2026-10-15T12:01:00+00:00")
    age = int((snapshot - latest).total_seconds())
    print("age_seconds", age)
    print("stale", age > 60)
