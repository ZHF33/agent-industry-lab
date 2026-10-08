import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def make_fixture(tmp_path):
    dify_output = tmp_path / "dify_output.json"
    image_prompt = tmp_path / "image_prompt.json"
    dify_output.write_text(
        json.dumps(
            {
                "data": {
                    "outputs": {
                        "content_plan": json.dumps({"angle": "bakery breakfast scene"}, ensure_ascii=False),
                        "xiaohongshu_copy": json.dumps({"title": "butter croissant morning"}, ensure_ascii=False),
                        "douyin_script": json.dumps({"hook": "first shot shows flaky layers"}, ensure_ascii=False),
                        "video_prompt": json.dumps({"scene": "natural light bakery product shot"}, ensure_ascii=False),
                        "compliance_result": json.dumps({"risk_level": "low"}, ensure_ascii=False),
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    image_prompt.write_text(
        json.dumps({"enhanced_prompt_en": "unbranded croissant, no embedded text"}, ensure_ascii=False),
        encoding="utf-8",
    )
    return dify_output, image_prompt


def test_create_approval_package_from_fixture(tmp_path):
    dify_output, image_prompt = make_fixture(tmp_path)
    out_dir = tmp_path / "approval_queue"

    subprocess.run(
        [
            sys.executable,
            "scripts/create_approval_package.py",
            "--input",
            str(dify_output),
            "--image-prompt",
            str(image_prompt),
            "--out-dir",
            str(out_dir),
        ],
        cwd=ROOT,
        check=True,
    )

    packages = list(out_dir.glob("run_*"))
    assert len(packages) == 1
    metadata = json.loads((packages[0] / "metadata.json").read_text(encoding="utf-8"))
    review = (packages[0] / "review.md").read_text(encoding="utf-8")
    assert metadata["approval_status"] == "pending"
    assert metadata["agent_name"] == "Bakery AI Operation Agent V2"
    assert metadata["assets"]["image_generation"]["status"] == "not_started"
    assert "Bakery AI Operation Agent V2" in review
    assert "Image Prompt" in review
    assert "Current Task Status" in review
    assert "Review Checklist" in review
    product_flow = (packages[0] / "product_flow.md").read_text(encoding="utf-8")
    assert "Product Operation Flow" in product_flow
    assert "Image Generation Plan" in product_flow
    assert (packages[0] / "tasks.json").exists()
    assert (packages[0] / "assets.json").exists()
