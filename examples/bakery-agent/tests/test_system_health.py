from pathlib import Path

from scripts import check_system_health


ROOT = Path(__file__).resolve().parents[1]


def test_health_required_env_keys_match_project_config():
    env_example = check_system_health.load_env(ROOT / ".env.example")
    for key in check_system_health.REQUIRED_ENV_KEYS:
        assert key in env_example


def test_health_runtime_db_checker_returns_list():
    issues = check_system_health.check_runtime_db()
    assert isinstance(issues, list)


def test_health_http_json_handles_unavailable_endpoint():
    ok, detail = check_system_health.http_json("http://127.0.0.1:1/health", timeout=1)
    assert ok is False
    assert detail


def test_health_http_post_json_handles_unavailable_endpoint():
    status, detail = check_system_health.http_post_json("http://127.0.0.1:1/operation", {"ok": True}, timeout=1)
    assert status == 0
    assert detail


def test_health_maps_docker_host_url_for_host_checks():
    assert check_system_health.host_reachable_url("http://host.docker.internal:8765") == "http://127.0.0.1:8765"
    assert check_system_health.host_reachable_url("http://agent-api:8765") == "http://127.0.0.1:8765"


def test_health_knows_full_pipeline_webhook_path():
    assert check_system_health.FULL_PIPELINE_WEBHOOK_PATH.endswith("/bakery-full-pipeline")
    assert "v2FullContentPipelineWebhook" in check_system_health.FULL_PIPELINE_WEBHOOK_PATH


def test_health_remediation_mentions_full_pipeline_ui_activation():
    remediation = "\n".join(check_system_health.FULL_PIPELINE_WEBHOOK_REMEDIATION)
    assert "http://localhost:5678/home/workflows" in remediation
    assert "v2_full_content_pipeline_webhook.json" in remediation
    assert "Turn the workflow Active" in remediation


def test_health_knows_full_pipeline_workflow_identity():
    assert check_system_health.FULL_PIPELINE_WORKFLOW_FILE == "n8n/workflows/v2_full_content_pipeline_webhook.json"
    assert check_system_health.FULL_PIPELINE_WORKFLOW_NAME == "V2 Full Content Pipeline Webhook"
