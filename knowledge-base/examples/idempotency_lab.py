"""Synthetic lecture experiments. No real model, workflow platform or external API."""
import json
import sqlite3
import sys
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from threading import Barrier

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from fastapi.testclient import TestClient
from industry_lab.api import create_app


def run_experiments(directory):
    root = Path(directory)
    path = root / "reviews.sqlite3"
    body = {"job_id": "lecture-demo", "product": {"name": "Demo Bread", "facts": {"ingredients": "flour", "storage": "cool place"}}, "claims": [], "copy": "Demo Bread", "max_chars": 100}
    with TestClient(create_app(path)) as client:
        first = client.post("/reviews", json=body)
        second = client.post("/reviews", json=body)
        assert first.status_code == second.status_code == 200
        assert first.json() == second.json()
        with closing(sqlite3.connect(path)) as db:
            assert db.execute("SELECT COUNT(*) FROM reviews").fetchone()[0] == 1
        assert client.post("/reviews", json={**body, "copy": "Changed"}).status_code == 409
        assert client.get("/reviews/lecture-demo").json() == first.json()
        assert client.post("/reviews/lecture-demo/decision", json={"decision": "rejected", "reviewer": "synthetic-operator", "note": "Demo revision needed"}).status_code == 200
    with TestClient(create_app(path)) as client:
        assert client.get("/reviews/lecture-demo").json()["status"] == "rejected"
        assert client.post("/reviews", json=body).json()["status"] == "rejected"
    print("PASS: repeated input creates one row; changed input conflicts; decision survives app reinitialization")

    with closing(sqlite3.connect(root / "transactions.sqlite3")) as db:
        db.execute("CREATE TABLE jobs(id TEXT PRIMARY KEY NOT NULL)")
        db.commit()
        try:
            with db:
                db.execute("INSERT INTO jobs VALUES (?)", ("rolled-back",))
                raise RuntimeError("synthetic failure")
        except RuntimeError:
            pass
        assert db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0
    print("PASS: exception rolls back the insert")

    concurrent_path = root / "concurrency.sqlite3"
    with closing(sqlite3.connect(concurrent_path)) as db:
        db.execute("CREATE TABLE jobs(id TEXT PRIMARY KEY NOT NULL)")
        db.commit()
    barrier = Barrier(2)
    def submit():
        with closing(sqlite3.connect(concurrent_path, timeout=5)) as db:
            barrier.wait(timeout=5)
            with db:
                db.execute("BEGIN IMMEDIATE")
                if db.execute("SELECT id FROM jobs WHERE id=?", ("same-task",)).fetchone():
                    return "reused"
                db.execute("INSERT INTO jobs VALUES (?)", ("same-task",))
                return "created"
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(submit) for _ in range(2)]
        results = [f.result(timeout=10) for f in futures]
    assert sorted(results) == ["created", "reused"]
    with closing(sqlite3.connect(concurrent_path)) as db:
        assert db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 1
    print("PASS: two database connections produce one create and one reuse")
    print(json.dumps({"scope": "local-synthetic-experiments", "model_verified": False, "platform_verified": False}))

def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--worker":
        run_experiments(sys.argv[2])
        return
    # Existing API connections close when this isolated process exits.
    with tempfile.TemporaryDirectory() as directory:
        subprocess.run([sys.executable, str(Path(__file__).resolve()), "--worker", directory], check=True)
    print("PASS: isolated worker exited and temporary databases were removed")


if __name__ == "__main__":
    main()
