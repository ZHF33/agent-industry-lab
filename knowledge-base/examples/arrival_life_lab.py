from datetime import datetime

arrival = datetime.fromisoformat("2026-11-10T12:00:00Z")
for text in ("2026-11-11T07:00:00-05:00", "2026-11-11T11:59:59Z"):
    remaining = int((datetime.fromisoformat(text) - arrival).total_seconds())
    print(remaining, remaining >= 24 * 3600)
