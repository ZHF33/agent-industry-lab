"""Compare declared acceptance conditions with scripted synthetic observations."""
import json


def check_report(report, expected):
    required = {"order_id", "verdict", "missing", "sources"}
    if not isinstance(report, dict) or set(report) != required:
        return "format_error"
    if (not isinstance(report["order_id"], str) or not isinstance(report["verdict"], str)
            or not isinstance(report["missing"], list) or not isinstance(report["sources"], list)):
        return "format_error"
    return "accepted" if report == expected else "content_error"


if __name__ == "__main__":
    expected = {"order_id": "DEMO-A", "verdict": "needs_evidence",
                "missing": ["return"], "sources": ["demo-01"]}
    for label, report in (
        ("normal", expected),
        ("missing_field", {key: value for key, value in expected.items() if key != "sources"}),
        ("unsupported_claim", {**expected, "verdict": "ready_for_review", "missing": []}),
    ):
        print(json.dumps({"case": label, "check": check_report(report, expected)}))
