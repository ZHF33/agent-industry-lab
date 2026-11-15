"""Process synthetic inspection records and preserve invalid rows."""
def summarize(records):
    summary = {"passed": 0, "failed": 0, "issues": []}
    for record in records:
        status = record.get("status")
        if status == "passed":
            summary["passed"] += 1
        elif status == "failed":
            summary["failed"] += 1
        else:
            summary["issues"].append(record["id"])
    return summary


if __name__ == "__main__":
    records = [
        {"id": "A", "status": "passed"},
        {"id": "B", "status": "failed"},
        {"id": "C"},
        {"id": "D", "status": 7},
    ]
    summary = summarize(records)
    print("passed", summary["passed"])
    print("failed", summary["failed"])
    print("issues", ",".join(summary["issues"]))
