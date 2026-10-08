from __future__ import annotations

import json
from typing import Any


DEFAULT_NEGATIVE = [
    "logo",
    "brand name",
    "trademark",
    "text",
    "signage",
    "official packaging",
    "unauthorized mark",
    "health claim",
    "nutrition claim",
    "price tag",
    "promotion label",
    "distorted food",
    "extra hands",
    "plastic-looking food",
    "messy background",
]

PHOTOGRAPHY_RULES = [
    "realistic commercial bakery photography",
    "clear product texture",
    "fresh baked surface detail",
    "soft natural window light",
    "clean bakery cafe setting",
    "premium but understated composition",
]

SOCIAL_CARD_RULES = [
    "square social media cover composition",
    "clear product hero subject",
    "generous negative space for later copy overlay",
    "mobile-first crop safety",
    "no embedded text in the image",
]


def parse_json_text(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        return {}
    text = value.strip()
    if text.startswith("```"):
        text = text.strip("`").replace("json\n", "", 1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


def clean_clause(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip().strip(".,; ")


def build_enhanced_prompt(
    outputs: dict[str, Any],
    *,
    product_query: str | None = None,
    content_task: dict[str, Any] | None = None,
    source: str = "runs/latest_dify_output.json",
) -> dict[str, Any]:
    content_task = content_task or {}
    product_name = product_query or content_task.get("product_name") or "bakery product"
    image_type = content_task.get("image_type") or "product_hero"
    image_style = content_task.get("image_style") or "realistic bakery product photography"
    visual_intent = clean_clause(content_task.get("visual_intent", ""))
    audience = content_task.get("audience") or "local bakery customers"

    image_prompt = parse_json_text(outputs.get("image_prompt", {}))
    xhs = parse_json_text(outputs.get("xiaohongshu_copy", {}))

    aspect_ratio = clean_clause(image_prompt.get("aspect_ratio", "")) or "1:1"
    prompt_en = clean_clause(image_prompt.get("prompt_en", ""))
    prompt_zh = clean_clause(image_prompt.get("prompt_zh", ""))

    product_subject = f"unbranded {image_type} for {product_name}"
    enhanced_en_parts = [
        f"{aspect_ratio} image, {product_subject}",
        image_style,
        f"operator visual intent: {visual_intent}" if visual_intent else "",
        f"intended audience: {audience}",
        prompt_en,
        ", ".join(PHOTOGRAPHY_RULES),
        ", ".join(SOCIAL_CARD_RULES),
        "review-ready social media visual for bakery operations",
    ]
    enhanced_en = ", ".join(part for part in enhanced_en_parts if part).replace(",,", ",")

    enhanced_zh_parts = [
        f"{aspect_ratio} social media image",
        f"unbranded bakery visual for {product_name}",
        image_type,
        image_style,
        f"operator visual intent: {visual_intent}" if visual_intent else "",
        prompt_zh,
        "realistic product texture",
        "soft natural window light",
        "clean bakery scene",
        "clear hero subject with safe empty space for later text overlay",
        "no text generated inside the image",
    ]
    enhanced_zh = ", ".join(part for part in enhanced_zh_parts if part)

    negative_prompt = ", ".join(DEFAULT_NEGATIVE)
    existing_negative = clean_clause(image_prompt.get("negative_prompt", ""))
    if existing_negative:
        negative_prompt = f"{existing_negative}, {negative_prompt}"

    return {
        "source": source,
        "content_task": content_task,
        "product_query": product_name,
        "aspect_ratio": aspect_ratio,
        "cover_text_suggestion": xhs.get("cover_text", ""),
        "enhanced_prompt_zh": enhanced_zh,
        "enhanced_prompt_en": enhanced_en,
        "negative_prompt": negative_prompt,
        "style_rules": {
            "photography": PHOTOGRAPHY_RULES,
            "social_card": SOCIAL_CARD_RULES,
        },
        "compliance_rules": [
            "Do not generate logos, brand names, official packaging, trademark-like marks, or embedded text.",
            "Do not imply health, nutrition, diet, or medical benefits.",
            "Do not create fake price, sales volume, inventory, or promotion labels.",
            "Generated image is for local workflow testing and requires human review.",
        ],
    }


def build_prompt_variants(payload: dict[str, Any], *, count: int = 3) -> list[dict[str, Any]]:
    content_task = payload.get("content_task", {})
    product_name = payload.get("product_query") or content_task.get("product_name") or "bakery product"
    requested_image_type = content_task.get("image_type") or "product_hero"
    base_en = payload.get("enhanced_prompt_en", "")
    base_zh = payload.get("enhanced_prompt_zh", "")
    variant_specs = [
        {
            "variant_id": "hero",
            "matches": {"product_hero", "product_display", "social_poster", "short_video_cover"},
            "title": "Product hero display",
            "en_suffix": "hero composition, product centered, clean bakery counter, strong silhouette, premium social cover",
            "zh_suffix": "product hero display, clean bakery counter, clear central subject",
        },
        {
            "variant_id": "deconstructed",
            "matches": {"deconstructed_exploded_view"},
            "title": "Deconstructed display",
            "en_suffix": "deconstructed exploded-view composition, neatly separated visible layers and fillings, no unrealistic floating fragments, ingredient facts only if visible or supplied",
            "zh_suffix": "deconstructed exploded-view display, neatly separated visible layers, no unsupported ingredients",
        },
        {
            "variant_id": "cutaway_detail",
            "matches": {"cutaway_detail"},
            "title": "Cutaway detail",
            "en_suffix": "cutaway detail composition, visible sliced interior, crumb, filling, and clean edge texture, realistic food photography",
            "zh_suffix": "cutaway detail display, visible sliced interior, crumb and filling texture",
        },
        {
            "variant_id": "texture_closeup",
            "matches": {"texture_closeup"},
            "title": "Texture close-up",
            "en_suffix": "macro texture close-up, crust and crumb detail, appetizing baked surface, shallow depth of field",
            "zh_suffix": "texture close-up, crust and crumb detail, appetizing baked surface",
        },
        {
            "variant_id": "lifestyle",
            "matches": {"lifestyle_scene", "breakfast_scene", "afternoon_tea_scene"},
            "title": "Bakery lifestyle scene",
            "en_suffix": "natural bakery cafe lifestyle scene, table setting, soft window light, review-ready commercial food photo",
            "zh_suffix": "bakery lifestyle scene, cafe table, soft natural light",
        },
    ]
    variant_specs = sorted(
        variant_specs,
        key=lambda spec: 0 if requested_image_type in spec.get("matches", set()) or spec["variant_id"] == requested_image_type else 1,
    )
    variants = []
    for spec in variant_specs[: max(1, count)]:
        variants.append(
            {
                "variant_id": spec["variant_id"],
                "title": spec["title"],
                "product_name": product_name,
                "prompt_en": ", ".join(part for part in [base_en, spec["en_suffix"]] if part),
                "prompt_zh": ", ".join(part for part in [base_zh, spec["zh_suffix"]] if part),
                "negative_prompt": payload.get("negative_prompt", ""),
                "aspect_ratio": payload.get("aspect_ratio", "1:1"),
                "status": "prepared",
            }
        )
    return variants


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Enhanced Image Prompt",
        "",
        f"- product_query: {payload['product_query']}",
        f"- aspect_ratio: {payload['aspect_ratio']}",
        f"- cover_text_suggestion: {payload.get('cover_text_suggestion', '')}",
        "",
        "## Content Task",
        "",
        "```json",
        json.dumps(payload.get("content_task", {}), ensure_ascii=False, indent=2),
        "```",
        "",
        "## Prompt ZH",
        "",
        payload["enhanced_prompt_zh"],
        "",
        "## Prompt EN",
        "",
        payload["enhanced_prompt_en"],
        "",
        "## Negative Prompt",
        "",
        payload["negative_prompt"],
        "",
        "## Compliance Rules",
        "",
    ]
    if payload.get("variants"):
        lines.extend(["## Variants", ""])
        for variant in payload["variants"]:
            lines.extend(
                [
                    f"### {variant['variant_id']}",
                    "",
                    variant.get("prompt_en", ""),
                    "",
                ]
            )
    lines.extend(f"- {rule}" for rule in payload["compliance_rules"])
    lines.append("")
    return "\n".join(lines)
