import sqlite3

from scripts import inspect_n8n_workflows


def make_db(path, rows):
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE workflow_entity (id TEXT, name TEXT, active INTEGER)")
        conn.executemany("INSERT INTO workflow_entity (id, name, active) VALUES (?, ?, ?)", rows)


def test_inspect_n8n_workflows_flags_inactive_required(tmp_path):
    db = tmp_path / "n8n.sqlite"
    make_db(
        db,
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

    result = inspect_n8n_workflows.inspect(db)

    assert result["ok"] is False
    assert result["inactive_required"] == [
        {"id": "v2FullContentPipelineWebhook", "name": "V2 Full Content Pipeline Webhook", "required": True}
    ]
    assert "turn Active on" in result["next_actions"][0]
    assert result["activation_steps"][0]["action"] == "open_n8n_workflows"
    assert any(step["action"] == "activate_workflow" and "V2 Full Content Pipeline Webhook" in step["detail"] for step in result["activation_steps"])
    assert any(step["action"] == "verify_full_pipeline_manual" for step in result["activation_steps"])
    assert any(step["action"] == "verify_full_pipeline_auto_acceptance" for step in result["activation_steps"])


def test_inspect_n8n_workflows_allows_optional_mock_missing(tmp_path):
    db = tmp_path / "n8n.sqlite"
    make_db(
        db,
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

    result = inspect_n8n_workflows.inspect(db)

    assert result["ok"] is True
    assert result["missing_required"] == []
    assert result["inactive_required"] == []
    assert result["activation_steps"] == [{"action": "ready", "detail": "All required V2 workflows are imported and active."}]
