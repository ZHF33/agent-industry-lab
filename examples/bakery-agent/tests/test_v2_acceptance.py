import json
import sqlite3
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_run_v2_acceptance_chain(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_v2_acceptance.py",
            "--base-dir",
            str(tmp_path / "acceptance"),
            "--request",
            "今日的爆品是牛肉恰巴塔，生成它的解构风展示图",
            "--json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )

    data = json.loads(result.stdout)
    package_dir = Path(data["package_dir"])
    metadata = json.loads((package_dir / "metadata.json").read_text(encoding="utf-8"))

    assert data["ok"] is True
    assert data["content_task"]["product_name"] == "牛肉恰巴塔"
    assert data["content_task"]["image_type"] == "deconstructed_exploded_view"
    assert data["final"]["approval_status"] == "approved"
    assert data["final"]["image_status"] == "completed"
    assert data["final"]["selected_image_id"]
    assert data["final"]["publish_status"] == "published"
    assert data["final"]["publish_record_count"] == 2
    assert (package_dir / "publish_draft.json").exists()
    assert (package_dir / "publish_record.json").exists()
    assert metadata["publish_records"][0]["platform"] == "xiaohongshu"
    assert metadata["publish_records"][1]["platform"] == "douyin"

    selected_image = metadata["assets"]["image_generation"]["selected_image"]
    assert selected_image["image_paths"]
    assert Path(selected_image["image_paths"][0]).exists()

    with sqlite3.connect(data["db"]) as conn:
        history = conn.execute(
            "SELECT platform FROM campaign_history WHERE run_id = ? ORDER BY platform",
            (data["run_id"],),
        ).fetchall()
    assert history == [("douyin",), ("xiaohongshu",)]


def test_run_v2_acceptance_via_n8n_requires_secret(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_v2_acceptance.py",
            "--via-n8n",
            "--env-file",
            str(tmp_path / "missing.env"),
            "--json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode != 0
    assert "N8N_WEBHOOK_SECRET is required" in result.stderr


def test_run_v2_acceptance_mock_publish_chain(tmp_path):
    env = tmp_path / ".env"
    env.write_text("MOCK_PUBLISH_ENABLED=true\nPUBLISH_CONNECTOR_MODE=mock\n", encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_v2_acceptance.py",
            "--base-dir",
            str(tmp_path / "acceptance"),
            "--env-file",
            str(env),
            "--mock-publish",
            "--json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )

    data = json.loads(result.stdout)
    package_dir = Path(data["package_dir"])
    metadata = json.loads((package_dir / "metadata.json").read_text(encoding="utf-8"))
    assert data["ok"] is True
    assert data["final"]["mock_publish_used"] is True
    assert len(data["mock_publish_results"]) == 2
    assert metadata["publish_records"][0]["published_url"].startswith("https://mock.local/")


def test_run_v2_acceptance_chain_accepts_non_beef_product(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_v2_acceptance.py",
            "--base-dir",
            str(tmp_path / "acceptance"),
            "--request",
            "今日新品是草莓拿破仑，生成它的下午茶场景图",
            "--preferred-image-id",
            "hero",
            "--json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )

    data = json.loads(result.stdout)
    assert data["ok"] is True
    assert data["content_task"]["product_name"] == "草莓拿破仑"
    assert data["content_task"]["image_type"] == "lifestyle_scene"
    assert data["final"]["publish_status"] == "published"
    assert data["final"]["publish_record_count"] == 2


def test_run_v2_acceptance_default_outputs_use_runs_directory(monkeypatch, tmp_path):
    from scripts import run_v2_acceptance

    class Args:
        base_dir = ""
        via_n8n = False
        via_n8n_full = False

    captured = {}

    def fake_run_content_operation(args, base_dir, db_path, log_path):
        captured["base_dir"] = str(base_dir)
        captured["db_path"] = str(db_path)
        captured["log_path"] = str(log_path)
        raise RuntimeError("stop after path selection")

    monkeypatch.setattr(run_v2_acceptance, "_run_content_operation", fake_run_content_operation)

    try:
        run_v2_acceptance.run_acceptance(Args())
    except RuntimeError as exc:
        assert "stop after path selection" in str(exc)
    else:
        raise AssertionError("Expected path-selection sentinel.")

    assert captured["base_dir"].endswith("runs")
    assert captured["db_path"].endswith("runs\\acceptance_ops.sqlite3") or captured["db_path"].endswith("runs/acceptance_ops.sqlite3")
    assert captured["log_path"].endswith("runs\\acceptance_operation_log.jsonl") or captured["log_path"].endswith("runs/acceptance_operation_log.jsonl")


def test_run_v2_acceptance_full_pipeline_manual_only_payload(monkeypatch):
    from scripts import run_v2_acceptance

    class Args:
        request = "今日的爆品是牛肉恰巴塔，生成它的解构风展示图"
        platforms = "xiaohongshu,douyin"
        image_count = 3
        preferred_image_id = "deconstructed"
        mock_publish = False
        image_note = "note"
        approval_note = "approval"
        timeout = 10
        manual_only = True

    captured = {}

    def fake_post_json(url, payload, timeout, headers):
        captured["payload"] = payload
        return {
            "ok": True,
            "pipeline": {
                "ok": True,
                "stage": "pending_approval",
                "run_id": "run_manual",
                "package_dir": "runs/approval_queue/run_manual",
            },
        }

    monkeypatch.setattr(run_v2_acceptance, "_post_json", fake_post_json)

    pipeline = run_v2_acceptance._run_full_pipeline_via_n8n(Args(), {"X-Bakery-Webhook-Secret": "secret"})

    assert pipeline["stage"] == "pending_approval"
    assert captured["payload"]["approval_mode"] == "manual"
    assert "auto_approve" not in captured["payload"]
    assert "approval_note" not in captured["payload"]


def test_run_v2_acceptance_formats_inactive_n8n_webhook_error():
    from scripts import run_v2_acceptance

    message = run_v2_acceptance._format_webhook_http_error(
        "http://localhost:5678/webhook/v2/full-content-pipeline",
        404,
        json.dumps(
            {
                "message": "The requested webhook is not registered.",
                "hint": "The workflow must be active for production webhooks.",
            }
        ),
    )

    assert "not registered" in message
    assert "turn Active on" in message
    assert "export_n8n_workflow_state.ps1" in message


def test_run_v2_acceptance_full_pipeline_runtime_preflight_blocks_inactive_workflow(tmp_path):
    from scripts import run_v2_acceptance

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

    try:
        run_v2_acceptance._preflight_full_pipeline_runtime(n8n_db)
    except RuntimeError as exc:
        message = str(exc)
    else:
        raise AssertionError("Expected inactive workflow preflight failure.")

    assert "before calling webhook" in message
    assert "V2 Full Content Pipeline Webhook" in message
    assert "turn Active on" in message


def test_run_v2_acceptance_mock_publish_requires_enable(tmp_path):
    env = tmp_path / ".env"
    env.write_text("PUBLISH_CONNECTOR_MODE=manual\n", encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_v2_acceptance.py",
            "--base-dir",
            str(tmp_path / "acceptance"),
            "--env-file",
            str(env),
            "--mock-publish",
            "--json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode != 0
    assert "Mock publish is disabled" in result.stderr
