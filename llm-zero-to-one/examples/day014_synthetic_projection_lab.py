"""Project a fixed synthetic record into a small public fixture."""
DEMO = {
    "shift_id": "SHIFT-DEMO-A",
    "window_minutes": 240,
    "gap_minutes": 20,
    "operator_note": "DEMO-NOTE: simulated field excluded from export",
}
PUBLIC_FIELDS = ("shift_id", "window_minutes", "gap_minutes")


def project(record):
    return {key: record[key] for key in PUBLIC_FIELDS}


if __name__ == "__main__":
    result = project(DEMO)
    print(result)
    print("note exported:", "operator_note" in result)
