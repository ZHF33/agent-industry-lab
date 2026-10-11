"""Standard-library analogy, not LangGraph or a model simulation."""
from copy import deepcopy

saved = {}
thread_id = "demo-task-1"
saved[thread_id] = {"status": "waiting_review", "difference": -6}
print(saved[thread_id]["status"])
resumed = deepcopy(saved[thread_id])
resumed["status"] = "reviewed"
saved[thread_id] = resumed
print(saved[thread_id]["status"])
saved.clear()
print("restart_lost" if thread_id not in saved else "unexpected")
