"""Read-only synthetic dependency experiment. Run manually."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "examples" / "task-dependency-review"))
from agent import inspect_dependencies, TASKS

if __name__ == "__main__":
    result = inspect_dependencies(TASKS["entries"])
    print("ready:", result["ready_pending_tasks"])
    print("waiting:", result["waiting_tasks"][0]["task_id"])
    print("cycle:", bool(result["cycle_example"]))
    cyclic = [{"task_id": "A", "status": "pending", "requires": ["B"]},
              {"task_id": "B", "status": "pending", "requires": ["A"]}]
    print("cycle example:", bool(inspect_dependencies(cyclic)["cycle_example"]))
