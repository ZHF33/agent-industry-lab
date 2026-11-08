"""Manual classroom reconciliation using the Agent's pure calculation."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "examples" / "inspection-reconciliation-review"))
from agent import CHECKLIST, OBSERVATIONS, reconcile

if __name__ == "__main__":
    report = reconcile(CHECKLIST["entries"], OBSERVATIONS["entries"])
    print("planned:", report["planned_count"])
    print("records:", report["observed_record_count"])
    print("matched:", report["matched_pair_count"])
    for label in ("missing", "unexpected", "multiple", "conflicts"):
        print(label + ":", [(r["device_id"], r["check_id"]) for r in report[label]])
