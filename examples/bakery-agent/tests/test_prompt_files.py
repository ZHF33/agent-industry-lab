from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_prompt_files_are_non_empty():
    prompts = list((ROOT / "dify" / "prompts").glob("*.md"))
    assert prompts
    for path in prompts:
        assert path.read_text(encoding="utf-8").strip(), path


def test_workflows_have_required_sections():
    workflows = list((ROOT / "dify" / "workflows").glob("*.workflow.md"))
    assert workflows
    for path in workflows:
        text = path.read_text(encoding="utf-8")
        for term in ["输入变量", "输出变量", "Prompt", "JSON", "失败处理"]:
            assert term in text, f"{path} missing {term}"


def test_bakery_v2_dify_workflow_is_image_first_without_video_node():
    workflow = yaml.safe_load((ROOT / "dify" / "workflows" / "bakery_operation_v1.dify.yml").read_text(encoding="utf-8"))
    nodes = workflow["workflow"]["graph"]["nodes"]
    edges = workflow["workflow"]["graph"]["edges"]
    node_ids = {node["id"] for node in nodes}
    output_variables = {
        output["variable"]
        for node in nodes
        if node["id"] == "end_node"
        for output in node["data"].get("outputs", [])
    }

    assert "video_prompt_generator" not in node_ids
    assert "video_prompt" not in output_variables
    assert any(edge["source"] == "image_prompt_generator" and edge["target"] == "compliance_reviewer" for edge in edges)
