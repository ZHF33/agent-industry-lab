"""Offline configuration/metadata lesson, never a TLS endpoint validation."""
from pathlib import Path
import ssl
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "examples" / "certificate-renewal-review"))
from agent import ASSETS, assess


def main():
    context = ssl.create_default_context()
    print("require_peer_certificate:", context.verify_mode == ssl.CERT_REQUIRED)
    print("check_hostname:", context.check_hostname)
    report = assess(ASSETS["CERT-DEMO-01"], "2026-10-20T13:00:00+00:00")
    for key in ["snapshot_urgency", "seconds_to_snapshot_expiry",
                "replacement_deployment", "current_endpoint_status"]:
        print(f"{key}: {report[key]}")


if __name__ == "__main__":
    main()
