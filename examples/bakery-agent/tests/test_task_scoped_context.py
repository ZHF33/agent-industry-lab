from services import knowledge_service
from scripts.run_content_operation import build_dify_payload


SAMPLE_CONTEXT = """# Bakery Agent Knowledge Context

## Brand Context

- Business type: local bakery and cafe.

## Supported Image Types

- `product_hero`: product as the central subject.
- `texture_closeup`: close-up of crust, crumb, layers, filling, or cut surface.

## Product Fact Examples

- Beef ciabatta: rustic ciabatta sandwich, sliced beef, cheese, lettuce, tomato, bakery cafe lunch scene.
- Butter croissant: laminated pastry, golden flaky layers, breakfast or bakery counter scene.
- Sourdough loaf: rustic loaf, crust and crumb texture, bakery shelf or cutting board scene.

## Platform Rules

- No fake prices or health claims.

## Output Expectation

- `content_plan`
- `image_prompt`
"""


def test_task_context_keeps_general_rules_and_current_task():
    context = knowledge_service.filter_task_knowledge_context(
        SAMPLE_CONTEXT,
        {
            "product_name": "Strawberry napoleon",
            "natural_request": "Create a lifestyle scene for Strawberry napoleon",
            "image_type": "lifestyle_scene",
            "platforms": "xiaohongshu,douyin",
        },
    )

    assert "## Brand Context" in context
    assert "## Current Task" in context
    assert "- product_name: Strawberry napoleon" in context
    assert "## Platform Rules" in context
    assert "## Output Expectation" in context


def test_task_context_keeps_only_matching_product_example():
    context = knowledge_service.filter_task_knowledge_context(
        SAMPLE_CONTEXT,
        {"product_name": "Beef ciabatta", "natural_request": "Today promote Beef ciabatta"},
    )

    assert "Beef ciabatta" in context
    assert "Butter croissant" not in context
    assert "Sourdough loaf" not in context


def test_task_context_does_not_match_product_by_image_type_only():
    context = knowledge_service.filter_task_knowledge_context(
        SAMPLE_CONTEXT,
        {
            "product_name": "Strawberry napoleon",
            "natural_request": "Create a texture closeup",
            "image_type": "texture_closeup",
        },
    )

    assert "Sourdough loaf" not in context
    assert "Beef ciabatta" not in context
    assert "No matching product example was found" in context


def test_task_context_truncates_after_filtering(tmp_path):
    context_path = tmp_path / "context.md"
    context_path.write_text(SAMPLE_CONTEXT + "\n" + ("extra " * 200), encoding="utf-8")

    context = knowledge_service.build_task_knowledge_context(
        {"product_name": "Beef ciabatta", "natural_request": "Beef ciabatta"},
        context_path,
        260,
    )

    assert len(context) <= 260
    assert "## Context Truncated" in context
    assert "Butter croissant" not in context


def test_build_dify_payload_uses_filtered_product_knowledge(tmp_path):
    context_path = tmp_path / "context.md"
    context_path.write_text(SAMPLE_CONTEXT, encoding="utf-8")

    payload = build_dify_payload(
        {
            "product_name": "Strawberry napoleon",
            "natural_request": "Create a lifestyle scene for Strawberry napoleon",
            "content_type": "new_product_launch",
            "image_type": "lifestyle_scene",
            "image_style": "natural bakery cafe lifestyle photography",
            "platforms": "xiaohongshu,douyin",
            "campaign_goal": "Generate review-ready content.",
            "audience": "local bakery customers",
            "constraints": "No fake claims.",
        },
        context_path,
        4800,
    )

    product_knowledge = payload["inputs"]["product_knowledge"]
    assert "Strawberry napoleon" in product_knowledge
    assert "Beef ciabatta" not in product_knowledge
    assert payload["inputs"]["brand_context"]
    assert payload["inputs"]["platform_rules"]
