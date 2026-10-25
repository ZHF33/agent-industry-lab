"""Offline inventory thought experiment; no storage SDK or network."""
from copy import deepcopy

VERSIONS = [
    {"id": "marker-v2", "kind": "delete_marker", "current": True, "body": None},
    {"id": "data-v1", "kind": "data", "current": False, "body": "synthetic receipt"},
]


def read_snapshot(versions, version_id=None):
    candidates = [v for v in versions if v["id"] == version_id] if version_id is not None else [v for v in versions if v["current"]]
    if len(candidates) != 1:
        raise ValueError("Exactly one selected version required")
    version = candidates[0]
    if version["kind"] == "delete_marker":
        return {"state": "hidden_by_marker", "body": None}
    if version["kind"] != "data":
        raise ValueError("Unknown kind")
    return {"state": "data", "body": version["body"]}


if __name__ == "__main__":
    versions = deepcopy(VERSIONS)
    print("default:", read_snapshot(versions)["state"])
    print("explicit:", read_snapshot(versions, "data-v1")["body"])
    print("data_versions:", sum(v["kind"] == "data" for v in versions))
