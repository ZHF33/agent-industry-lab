from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_v2_docs_point_to_agent_api_webhook_runtime():
    execution_plan = (ROOT / "docs" / "v2_0_execution_plan.md").read_text(encoding="utf-8")
    roadmap = (ROOT / "docs" / "optimization_roadmap.md").read_text(encoding="utf-8")
    architecture = (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")

    assert "Agent API /pipeline" in execution_plan
    assert "v2_full_content_pipeline_webhook.json" in execution_plan
    assert "notification placeholder" not in execution_plan
    assert "Agent API and V2 n8n webhooks" in roadmap
    assert "image placeholder or real API" not in roadmap
    assert "current V2 runtime uses HTTP webhooks" in architecture
