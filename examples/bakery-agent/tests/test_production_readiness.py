import json
import sqlite3
import subprocess
import sys
from pathlib import Path

from scripts import production_readiness


ROOT = Path(__file__).resolve().parents[1]


def make_complete_package(tmp_path: Path) -> Path:
    queue = tmp_path / "approval_queue"
    package = queue / "run_ready"
    image = tmp_path / "generated_images" / "demo.png"
    image.parent.mkdir(parents=True)
    image.write_bytes(b"png")
    package.mkdir(parents=True)
    metadata = {
        "run_id": "run_ready",
        "product_name": "牛肉恰巴塔",
        "platform": "xiaohongshu,douyin",
        "approval_status": "approved",
        "image_status": "completed",
        "selected_image_id": "deconstructed",
        "publish_status": "published",
        "publish_records": [{"platform": "xiaohongshu"}, {"platform": "douyin"}],
        "assets": {
            "image_generation": {
                "selected_image_id": "deconstructed",
                "selected_image": {"image_paths": [str(image)]},
            }
        },
    }
    (package / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")
    return queue


def test_latest_complete_run_detects_published_package(tmp_path):
    queue = make_complete_package(tmp_path)

    latest = production_readiness._latest_complete_run(queue)

    assert latest["found"] is True
    assert latest["run_id"] == "run_ready"
    assert latest["platforms"] == ["xiaohongshu", "douyin"]


def test_production_readiness_report_is_stage_based(tmp_path, monkeypatch):
    monkeypatch.setattr(production_readiness.check_system_health, "check_runtime_db", lambda: [])
    queue = make_complete_package(tmp_path)
    env = tmp_path / ".env"
    env.write_text(
        "\n".join(
            [
                "AGENT_API_TOKEN=token",
                "N8N_WEBHOOK_SECRET=secret",
                "N8N_BASE_URL=http://localhost:5678",
                "AGENT_API_URL=http://agent-api:8765",
                "AGENT_API_ALLOW_LIVE_IMAGE=false",
            ]
        ),
        encoding="utf-8",
    )

    report = production_readiness.build_report(env, queue)

    assert report["production_ready"] is False
    assert report["stages"]["local_demo_chain"]["ok"] is True
    assert report["stages"]["n8n_orchestration"]["ok"] is False
    assert any("runtime workflow state has not been checked" in blocker for blocker in report["stages"]["n8n_orchestration"]["blockers"])
    assert report["stages"]["live_image_generation"]["ok"] is False
    assert report["stages"]["external_auto_publish"]["ok"] is False
    assert report["stages"]["external_auto_publish"]["evidence"]["manual_record_ready"] is True


def test_production_readiness_runtime_db_can_clear_n8n_orchestration_stage(tmp_path, monkeypatch):
    monkeypatch.setattr(production_readiness.check_system_health, "check_runtime_db", lambda: [])
    queue = make_complete_package(tmp_path)
    env = tmp_path / ".env"
    env.write_text(
        "AGENT_API_TOKEN=x\nN8N_WEBHOOK_SECRET=x\nN8N_BASE_URL=http://localhost:5678\nAGENT_API_URL=http://agent-api:8765\n",
        encoding="utf-8",
    )
    n8n_db = tmp_path / "n8n.sqlite"
    with sqlite3.connect(n8n_db) as conn:
        conn.execute("CREATE TABLE workflow_entity (id TEXT, name TEXT, active INTEGER)")
        conn.executemany(
            "INSERT INTO workflow_entity (id, name, active) VALUES (?, ?, ?)",
            [
                ("v2FullContentPipelineWebhook", "V2 Full Content Pipeline Webhook", 1),
                ("v2ContentOperationWebhook", "V2 Content Operation Webhook", 1),
                ("v2ApprovalReviewWebhook", "V2 Approval Review Webhook", 1),
                ("v2ImageGenerationWebhook", "V2 Image Generation Webhook", 1),
                ("v2ImageSelectionWebhook", "V2 Image Selection Webhook", 1),
                ("v2PublishDraftWebhook", "V2 Publish Draft Webhook", 1),
                ("v2PublishRecordWebhook", "V2 Publish Record Webhook", 1),
            ],
        )

    report = production_readiness.build_report(env, queue, n8n_db)

    assert report["stages"]["n8n_orchestration"]["ok"] is True
    assert report["stages"]["n8n_orchestration"]["evidence"]["runtime"]["checked"] is True


def test_production_readiness_uses_n8n_runtime_db_when_provided(tmp_path):
    queue = make_complete_package(tmp_path)
    env = tmp_path / ".env"
    env.write_text(
        "AGENT_API_TOKEN=x\nN8N_WEBHOOK_SECRET=x\nN8N_BASE_URL=http://localhost:5678\nAGENT_API_URL=http://agent-api:8765\n",
        encoding="utf-8",
    )
    n8n_db = tmp_path / "n8n.sqlite"
    with sqlite3.connect(n8n_db) as conn:
        conn.execute("CREATE TABLE workflow_entity (id TEXT, name TEXT, active INTEGER)")
        conn.executemany(
            "INSERT INTO workflow_entity (id, name, active) VALUES (?, ?, ?)",
            [
                ("v2FullContentPipelineWebhook", "V2 Full Content Pipeline Webhook", 0),
                ("v2ContentOperationWebhook", "V2 Content Operation Webhook", 1),
                ("v2ApprovalReviewWebhook", "V2 Approval Review Webhook", 1),
                ("v2ImageGenerationWebhook", "V2 Image Generation Webhook", 1),
                ("v2ImageSelectionWebhook", "V2 Image Selection Webhook", 1),
                ("v2PublishDraftWebhook", "V2 Publish Draft Webhook", 1),
                ("v2PublishRecordWebhook", "V2 Publish Record Webhook", 1),
            ],
        )

    report = production_readiness.build_report(env, queue, n8n_db)

    assert report["stages"]["n8n_orchestration"]["ok"] is False
    assert any("inactive" in blocker and "V2 Full Content Pipeline Webhook" in blocker for blocker in report["stages"]["n8n_orchestration"]["blockers"])
    assert report["stages"]["n8n_orchestration"]["evidence"]["runtime"]["checked"] is True


def test_production_readiness_cli_json(tmp_path):
    queue = make_complete_package(tmp_path)
    env = tmp_path / ".env"
    env.write_text("AGENT_API_TOKEN=x\nN8N_WEBHOOK_SECRET=x\nN8N_BASE_URL=x\nAGENT_API_URL=x\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/production_readiness.py",
            "--env-file",
            str(env),
            "--queue",
            str(queue),
            "--json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )

    data = json.loads(result.stdout)
    assert data["summary"] == "not_ready"
    assert "local_demo_chain" in data["stages"]
