from datetime import datetime, timezone

events = [
    ("2026-11-13T13:00:00Z", "residue"),
    ("2026-11-13T13:10:00Z", "clear"),
    ("2026-11-13T08:10:00-05:00", "residue"),
]


def latest_state(records):
    parsed = [(datetime.fromisoformat(at).astimezone(timezone.utc), state) for at, state in records]
    newest = max(at for at, _ in parsed)
    states = {state for at, state in parsed if at == newest}
    return "conflict" if len(states) > 1 else next(iter(states))


print(latest_state(events))
print(latest_state([*events[:-1], (events[-1][0], "clear")]))
print(latest_state(reversed(events)))
