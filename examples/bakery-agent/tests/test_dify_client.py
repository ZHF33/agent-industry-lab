from services import dify_client


def test_workflow_url_preserves_configured_docker_host():
    assert dify_client.workflow_url("http://host.docker.internal:8080") == "http://host.docker.internal:8080/v1/workflows/run"
