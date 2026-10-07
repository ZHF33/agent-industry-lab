"""Local review Skill. No model verdict or external publication is implied."""
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


class Product(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    facts: dict[str, str]


class Claim(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    fact_key: str = Field(min_length=1, max_length=100)
    fact_value: str = Field(min_length=1, max_length=2000)


class ReviewInput(BaseModel):
    job_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,80}$")
    product: Product
    claims: list[Claim] = Field(max_length=100)
    content: str = Field(alias="copy", min_length=1, max_length=20000)
    max_chars: int = Field(ge=1, le=20000)


class Decision(BaseModel):
    decision: Literal["approved", "rejected", "needs_revision"]
    reviewer: str = Field(min_length=1, max_length=100)
    note: str = Field(min_length=1, max_length=2000)


def review(body: ReviewInput) -> dict:
    issues = []
    for key in ("ingredients", "storage"):
        if not body.product.facts.get(key, "").strip():
            issues.append({"code": "missing_fact", "source": f"product.facts.{key}"})
    if len(body.content) > body.max_chars:
        issues.append({"code": "channel_limit", "source": "copy"})
    for index, claim in enumerate(body.claims):
        actual = body.product.facts.get(claim.fact_key)
        if actual != claim.fact_value:
            issues.append({"code": "evidence_mismatch", "source": f"claims.{index}", "fact_key": claim.fact_key})
    return {"job_id": body.job_id, "status": "pending_review", "issues": issues,
            "semantic_verified": False,
            "human_checks": ["Check full copy for undeclared claims and semantic support; verify product facts."],
            "evidence": [c.model_dump() for c in body.claims]}


def create_app(db_path: Path) -> FastAPI:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as db:
        db.execute("CREATE TABLE IF NOT EXISTS reviews (id TEXT PRIMARY KEY, digest TEXT NOT NULL, report TEXT NOT NULL)")
        db.execute("CREATE TABLE IF NOT EXISTS decisions (id TEXT, decision TEXT, reviewer TEXT, note TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
    app = FastAPI(title="Bakery Content Review Skill", version="0.1.0")

    @app.get("/health")
    def health():
        return {"status": "ok", "mode": "local_review_skill"}

    @app.post("/reviews")
    def submit(body: ReviewInput):
        digest = hashlib.sha256(json.dumps(body.model_dump(), sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        with sqlite3.connect(db_path, timeout=10) as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute("SELECT digest, report FROM reviews WHERE id=?", (body.job_id,)).fetchone()
            if existing:
                if existing[0] != digest:
                    raise HTTPException(409, "job_id already used with different input")
                return json.loads(existing[1])
            report = review(body)
            db.execute("INSERT INTO reviews VALUES (?,?,?)", (body.job_id, digest, json.dumps(report)))
            return report

    @app.get("/reviews/{job_id}")
    def fetch(job_id: str):
        with sqlite3.connect(db_path) as db:
            row = db.execute("SELECT report FROM reviews WHERE id=?", (job_id,)).fetchone()
        if not row:
            raise HTTPException(404, "review not found")
        return json.loads(row[0])

    @app.post("/reviews/{job_id}/decision")
    def decide(job_id: str, body: Decision):
        with sqlite3.connect(db_path, timeout=10) as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT report FROM reviews WHERE id=?", (job_id,)).fetchone()
            if not row:
                raise HTTPException(404, "review not found")
            report = json.loads(row[0])
            if body.decision == "approved" and report["issues"]:
                raise HTTPException(422, "resolve issues in a new revision before approval")
            if report["status"] != "pending_review":
                raise HTTPException(409, "decision already recorded; submit a new revision")
            report["status"] = body.decision
            db.execute("UPDATE reviews SET report=? WHERE id=?", (json.dumps(report), job_id))
            db.execute("INSERT INTO decisions (id,decision,reviewer,note) VALUES (?,?,?,?)", (job_id, body.decision, body.reviewer, body.note))
        return report

    return app


def app_factory():
    return create_app(Path("runtime/reviews.sqlite3"))
