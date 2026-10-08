import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def test_n8n_v20_production_webhook_workflow():
    workflow = json.loads((ROOT / "n8n" / "workflows" / "v2_content_operation_webhook.json").read_text(encoding="utf-8"))
    assert workflow["active"] is False
    node_names = {node["name"] for node in workflow["nodes"]}
    assert "Daily Trigger" not in node_names
    assert "Run V2 Content Operation" not in node_names
    assert "ContentRequestWebhook" in node_names
    assert "Call Bakery Agent API" in node_names
    assert "Webhook Response" in node_names
    webhook = next(node for node in workflow["nodes"] if node["name"] == "ContentRequestWebhook")
    assert webhook["parameters"]["path"] == "bakery-content-request"
    assert webhook["parameters"]["responseMode"] == "lastNode"
    http_node = next(node for node in workflow["nodes"] if node["name"] == "Call Bakery Agent API")
    assert http_node["type"] == "n8n-nodes-base.httpRequest"
    assert "AGENT_API_URL" in http_node["parameters"]["url"]
    assert "http://agent-api:8765" in http_node["parameters"]["url"]
    assert http_node["parameters"]["sendHeaders"] is True
    assert "AGENT_API_TOKEN" in json.dumps(http_node["parameters"].get("headerParameters", {}))
    code_blocks = [node["parameters"].get("jsCode", "") for node in workflow["nodes"]]
    assert any("body" in code and "user_request" in code for code in code_blocks)
    assert any("image_count must be an integer between 1 and 8" in code for code in code_blocks)
    assert any("live_image is not allowed in the content webhook" in code for code in code_blocks)
    assert any("N8N_WEBHOOK_SECRET" in code and "Unauthorized webhook request" in code for code in code_blocks)


def test_n8n_v20_full_pipeline_webhook_workflow():
    workflow = json.loads((ROOT / "n8n" / "workflows" / "v2_full_content_pipeline_webhook.json").read_text(encoding="utf-8"))
    assert workflow["active"] is False
    node_names = {node["name"] for node in workflow["nodes"]}
    node_types = {node["type"] for node in workflow["nodes"]}
    assert "FullPipelineWebhook" in node_names
    assert "Full Pipeline Input" in node_names
    assert "Call Full Pipeline API" in node_names
    assert "n8n-nodes-base.executeCommand" not in node_types
    webhook = next(node for node in workflow["nodes"] if node["name"] == "FullPipelineWebhook")
    assert webhook["parameters"]["path"] == "bakery-full-pipeline"
    http_node = next(node for node in workflow["nodes"] if node["name"] == "Call Full Pipeline API")
    assert http_node["type"] == "n8n-nodes-base.httpRequest"
    assert "/pipeline" in http_node["parameters"]["url"]
    assert "http://agent-api:8765" in http_node["parameters"]["url"]
    assert "AGENT_API_TOKEN" in json.dumps(http_node["parameters"].get("headerParameters", {}))
    code_blocks = [node["parameters"].get("jsCode", "") for node in workflow["nodes"]]
    assert any("user_request is required" in code and "mock_publish" in code for code in code_blocks)
    assert any("mock_publish: incoming.mock_publish !== undefined ? Boolean(incoming.mock_publish) : false" in code for code in code_blocks)
    assert any("approval_mode: incoming.approval_mode || (autoApprove ? 'auto' : 'manual')" in code for code in code_blocks)
    assert any("auto_approve=true was explicitly requested" in code and ": '')" in code for code in code_blocks)
    assert any("image_count must be an integer between 1 and 8" in code for code in code_blocks)
    assert any("N8N_WEBHOOK_SECRET" in code and "Unauthorized webhook request" in code for code in code_blocks)


def test_n8n_active_workflow_directory_excludes_legacy_placeholders():
    workflow_names = {path.name for path in (ROOT / "n8n" / "workflows").glob("*.json")}
    assert "daily_content_factory.json" not in workflow_names
    assert "local_dify_call_test.json" not in workflow_names
    assert not any("placeholder" in name for name in workflow_names)
    for path in (ROOT / "n8n" / "workflows").glob("v2_*.json"):
        text = path.read_text(encoding="utf-8").lower()
        if path.name != "v2_content_operation_execute_command.json":
            assert "executecommand" not in text
        assert "chagee" not in text
        assert "霸王茶姬" not in text


def test_n8n_v20_approval_review_webhook_workflow():
    workflow = json.loads((ROOT / "n8n" / "workflows" / "v2_approval_review_webhook.json").read_text(encoding="utf-8"))
    assert workflow["active"] is False
    node_names = {node["name"] for node in workflow["nodes"]}
    assert "ApprovalReviewWebhook" in node_names
    assert "Approval Review Input" in node_names
    assert "Call Approval Review API" in node_names
    webhook = next(node for node in workflow["nodes"] if node["name"] == "ApprovalReviewWebhook")
    assert webhook["parameters"]["path"] == "bakery-approval-review"
    http_node = next(node for node in workflow["nodes"] if node["name"] == "Call Approval Review API")
    assert "/approval/review" in http_node["parameters"]["url"]
    assert "http://agent-api:8765" in http_node["parameters"]["url"]
    assert "AGENT_API_TOKEN" in json.dumps(http_node["parameters"].get("headerParameters", {}))
    code_blocks = [node["parameters"].get("jsCode", "") for node in workflow["nodes"]]
    assert any("N8N_WEBHOOK_SECRET" in code and "Unauthorized webhook request" in code for code in code_blocks)


def test_n8n_v20_image_generation_webhook_workflow():
    workflow = json.loads((ROOT / "n8n" / "workflows" / "v2_image_generation_webhook.json").read_text(encoding="utf-8"))
    assert workflow["active"] is False
    node_names = {node["name"] for node in workflow["nodes"]}
    assert "ImageGenerationWebhook" in node_names
    assert "Image Generation Input" in node_names
    assert "Call Image Generation API" in node_names
    assert "Run V2 Content Operation" not in node_names
    webhook = next(node for node in workflow["nodes"] if node["name"] == "ImageGenerationWebhook")
    assert webhook["parameters"]["path"] == "bakery-image-generate"
    http_node = next(node for node in workflow["nodes"] if node["name"] == "Call Image Generation API")
    assert http_node["type"] == "n8n-nodes-base.httpRequest"
    assert "/image/generate" in http_node["parameters"]["url"]
    assert "http://agent-api:8765" in http_node["parameters"]["url"]
    assert "AGENT_API_TOKEN" in json.dumps(http_node["parameters"].get("headerParameters", {}))
    code_blocks = [node["parameters"].get("jsCode", "") for node in workflow["nodes"]]
    assert any("package is required" in code for code in code_blocks)
    assert any("n must be an integer between 1 and 8" in code for code in code_blocks)
    assert any("local_demo" in code and "cannot both be true" in code for code in code_blocks)
    assert all("allow_unapproved" not in code for code in code_blocks)
    assert any("N8N_WEBHOOK_SECRET" in code and "Unauthorized webhook request" in code for code in code_blocks)


def test_n8n_v20_image_selection_webhook_workflow():
    workflow = json.loads((ROOT / "n8n" / "workflows" / "v2_image_selection_webhook.json").read_text(encoding="utf-8"))
    assert workflow["active"] is False
    node_names = {node["name"] for node in workflow["nodes"]}
    assert "ImageSelectionWebhook" in node_names
    assert "Image Selection Input" in node_names
    assert "Call Image Selection API" in node_names
    webhook = next(node for node in workflow["nodes"] if node["name"] == "ImageSelectionWebhook")
    assert webhook["parameters"]["path"] == "bakery-image-select"
    http_node = next(node for node in workflow["nodes"] if node["name"] == "Call Image Selection API")
    assert http_node["type"] == "n8n-nodes-base.httpRequest"
    assert "/image/select" in http_node["parameters"]["url"]
    assert "http://agent-api:8765" in http_node["parameters"]["url"]
    assert "AGENT_API_TOKEN" in json.dumps(http_node["parameters"].get("headerParameters", {}))
    code_blocks = [node["parameters"].get("jsCode", "") for node in workflow["nodes"]]
    assert any("package is required" in code and "image_id is required" in code for code in code_blocks)
    assert any("N8N_WEBHOOK_SECRET" in code and "Unauthorized webhook request" in code for code in code_blocks)


def test_n8n_v20_publish_draft_webhook_workflow():
    workflow = json.loads((ROOT / "n8n" / "workflows" / "v2_publish_draft_webhook.json").read_text(encoding="utf-8"))
    assert workflow["active"] is False
    node_names = {node["name"] for node in workflow["nodes"]}
    assert "PublishDraftWebhook" in node_names
    assert "Publish Draft Input" in node_names
    assert "Call Publish Draft API" in node_names
    assert "Run V2 Content Operation" not in node_names
    webhook = next(node for node in workflow["nodes"] if node["name"] == "PublishDraftWebhook")
    assert webhook["parameters"]["path"] == "bakery-publish-draft"
    http_node = next(node for node in workflow["nodes"] if node["name"] == "Call Publish Draft API")
    assert http_node["type"] == "n8n-nodes-base.httpRequest"
    assert "/publish/draft" in http_node["parameters"]["url"]
    assert "http://agent-api:8765" in http_node["parameters"]["url"]
    assert "AGENT_API_TOKEN" in json.dumps(http_node["parameters"].get("headerParameters", {}))
    code_blocks = [node["parameters"].get("jsCode", "") for node in workflow["nodes"]]
    assert any("package is required" in code for code in code_blocks)
    assert any("N8N_WEBHOOK_SECRET" in code and "Unauthorized webhook request" in code for code in code_blocks)


def test_n8n_v20_publish_record_webhook_workflow():
    workflow = json.loads((ROOT / "n8n" / "workflows" / "v2_publish_record_webhook.json").read_text(encoding="utf-8"))
    assert workflow["active"] is False
    node_names = {node["name"] for node in workflow["nodes"]}
    assert "PublishRecordWebhook" in node_names
    assert "Publish Record Input" in node_names
    assert "Call Publish Record API" in node_names
    webhook = next(node for node in workflow["nodes"] if node["name"] == "PublishRecordWebhook")
    assert webhook["parameters"]["path"] == "bakery-publish-record"
    http_node = next(node for node in workflow["nodes"] if node["name"] == "Call Publish Record API")
    assert http_node["type"] == "n8n-nodes-base.httpRequest"
    assert "/publish/record" in http_node["parameters"]["url"]
    assert "http://agent-api:8765" in http_node["parameters"]["url"]
    assert "AGENT_API_TOKEN" in json.dumps(http_node["parameters"].get("headerParameters", {}))
    code_blocks = [node["parameters"].get("jsCode", "") for node in workflow["nodes"]]
    assert any("package is required" in code and "platform is required" in code for code in code_blocks)
    assert any("N8N_WEBHOOK_SECRET" in code and "Unauthorized webhook request" in code for code in code_blocks)


def test_n8n_v20_publish_mock_webhook_workflow():
    workflow = json.loads((ROOT / "n8n" / "workflows" / "v2_publish_mock_webhook.json").read_text(encoding="utf-8"))
    assert workflow["active"] is False
    node_names = {node["name"] for node in workflow["nodes"]}
    assert "PublishMockWebhook" in node_names
    assert "Publish Mock Input" in node_names
    assert "Call Publish Mock API" in node_names
    webhook = next(node for node in workflow["nodes"] if node["name"] == "PublishMockWebhook")
    assert webhook["parameters"]["path"] == "bakery-publish-mock"
    http_node = next(node for node in workflow["nodes"] if node["name"] == "Call Publish Mock API")
    assert http_node["type"] == "n8n-nodes-base.httpRequest"
    assert "/publish/mock" in http_node["parameters"]["url"]
    assert "http://agent-api:8765" in http_node["parameters"]["url"]
    assert "AGENT_API_TOKEN" in json.dumps(http_node["parameters"].get("headerParameters", {}))
    code_blocks = [node["parameters"].get("jsCode", "") for node in workflow["nodes"]]
    assert any("package is required" in code and "platform is required" in code for code in code_blocks)
    assert any("N8N_WEBHOOK_SECRET" in code and "Unauthorized webhook request" in code for code in code_blocks)


def test_current_docs_point_to_v20_execution_path():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    architecture = (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
    for text in [readme, architecture]:
        assert "scripts/run_content_operation.py" in text
        assert "n8n/workflows/v2_full_content_pipeline_webhook.json" in text
        assert "n8n/workflows/v2_content_operation_execute_command.json" not in text
        assert "n8n/workflows/v2_image_selection_webhook.json" in text
        assert "n8n/workflows/v2_publish_draft_webhook.json" in text
        assert "n8n/workflows/v2_publish_record_webhook.json" in text
        assert "n8n/workflows/v2_publish_mock_webhook.json" in text
    assert re.search(r"V2\\.0|V2", readme)

