"""Offline metadata comparison only; never creates or restores backup files."""
import copy
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "examples" / "backup-recovery-review"))
from agent import SYSTEMS, assess


def main():
    record = copy.deepcopy(SYSTEMS["RECOVERY-DEMO-01"])
    result = assess(record, "2026-10-21T13:04:00+00:00")
    print("point_lag_seconds:", result["recorded_point_lag_seconds"])
    print("historical_service_ready_seconds:", result["recorded_service_ready_seconds"])
    print("rpo_evidence:", result["rpo_evidence"])
    print("drill_fresh:", result["drill_fresh"])
    print("actual_recoverability:", result["actual_recoverability"])
    # Change only the recorded recovery point, not completion time.
    record["recovery_point_at"] = "2026-10-21T12:40:00+00:00"
    changed = assess(record, "2026-10-21T13:04:00+00:00")
    print("older_point_rpo:", changed["rpo_evidence"])


if __name__ == "__main__":
    main()
