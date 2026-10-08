import json
import subprocess
import sys
from pathlib import Path

from services import image_prompt_service

ROOT = Path(__file__).resolve().parents[1]


def test_enhance_image_prompt_with_fixture(tmp_path):
    fixture = tmp_path / "dify_output.json"
    out_json = tmp_path / "image_prompt.json"
    out_md = tmp_path / "image_prompt.md"
    fixture.write_text(
        json.dumps(
            {
                "data": {
                    "outputs": {
                        "image_prompt": json.dumps(
                            {
                                "prompt_zh": "一杯原叶鲜奶茶，干净桌面，自然光。",
                                "prompt_en": "A cup of modern oriental milk tea on a clean table.",
                                "negative_prompt": "无Logo",
                                "aspect_ratio": "1:1",
                            },
                            ensure_ascii=False,
                        ),
                        "xiaohongshu_copy": json.dumps({"cover_text": "茶香奶香刚刚好"}, ensure_ascii=False),
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            "scripts/enhance_image_prompt.py",
            "--input",
            str(fixture.relative_to(ROOT)) if fixture.is_relative_to(ROOT) else str(fixture),
            "--out-json",
            str(out_json),
            "--out-md",
            str(out_md),
        ],
        cwd=ROOT,
        check=True,
    )
    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert "enhanced_prompt_en" in data
    assert "no embedded text" in data["enhanced_prompt_en"]
    assert "logo" in data["negative_prompt"].lower()
    assert out_md.exists()


def test_enhanced_prompt_includes_operator_visual_intent():
    payload = image_prompt_service.build_enhanced_prompt(
        {
            "image_prompt": {
                "prompt_en": "clean bakery counter",
                "aspect_ratio": "1:1",
            },
            "xiaohongshu_copy": {},
        },
        content_task={
            "product_name": "Lemon croissant",
            "image_type": "product_hero",
            "image_style": "realistic bakery product photography",
            "visual_intent": "low-saturation magazine-style display image",
        },
    )

    assert "low-saturation magazine-style display image" in payload["enhanced_prompt_en"]
    assert "low-saturation magazine-style display image" in payload["enhanced_prompt_zh"]


def test_prompt_variants_prioritize_requested_image_type():
    payload = image_prompt_service.build_enhanced_prompt(
        {"image_prompt": {"prompt_en": "clean cutaway", "aspect_ratio": "1:1"}, "xiaohongshu_copy": {}},
        content_task={
            "product_name": "Black sesame bagel",
            "image_type": "cutaway_detail",
            "image_style": "realistic bakery cutaway detail photography",
            "visual_intent": "cutaway close-up image",
        },
    )

    variants = image_prompt_service.build_prompt_variants(payload, count=2)

    assert [variant["variant_id"] for variant in variants] == ["cutaway_detail", "hero"]
    assert "visible sliced interior" in variants[0]["prompt_en"]
