from __future__ import annotations

import re
from typing import Any


STYLE_MAP = [
    ("解构", "deconstructed_exploded_view", "deconstructed exploded-view bakery product display, neatly separated visible layers and ingredients"),
    ("拆解", "deconstructed_exploded_view", "deconstructed exploded-view bakery product display, neatly separated visible layers and ingredients"),
    ("分层", "deconstructed_exploded_view", "deconstructed layered bakery product display, visible fillings and structure"),
    ("切面", "cutaway_detail", "realistic bakery cutaway detail photography, visible crumb, filling, and texture"),
    ("剖面", "cutaway_detail", "realistic bakery cutaway detail photography, visible crumb, filling, and texture"),
    ("近景", "texture_closeup", "close-up bakery texture photography"),
    ("特写", "texture_closeup", "close-up bakery texture photography"),
    ("细节", "texture_closeup", "close-up bakery texture photography"),
    ("场景", "lifestyle_scene", "natural bakery cafe lifestyle photography"),
    ("氛围", "lifestyle_scene", "natural bakery cafe lifestyle photography"),
    ("生活方式", "lifestyle_scene", "natural bakery cafe lifestyle photography"),
    ("封面", "short_video_cover", "social media cover image, clear product hero subject"),
    ("海报", "social_poster", "clean social media bakery poster-style product photography without embedded text"),
    ("主图", "product_hero", "realistic bakery product hero photography"),
    ("展示图", "product_display", "realistic product display photography"),
]

CONTENT_TYPE_MAP = [
    ("爆品", "best_seller_feature"),
    ("热卖", "best_seller_feature"),
    ("主推", "featured_product"),
    ("新品", "new_product_launch"),
    ("上新", "new_product_launch"),
    ("节日", "seasonal_campaign"),
    ("早餐", "breakfast_scene"),
    ("下午茶", "afternoon_tea_scene"),
]

PLATFORM_KEYWORDS = {
    "小红书": "xiaohongshu",
    "抖音": "douyin",
    "视频号": "wechat_channels",
    "朋友圈": "wechat_moments",
}


def _extract_product(text: str) -> str:
    patterns = [
        r"(?:今日|今天|明天|本周|这个月)?(?:的)?(?:爆品|热卖|主推|新品|上新|推荐|招牌)(?:是|：|:)?([^，。,.]+)",
        r"(?:产品|商品|单品)(?:是|：|:)([^，。,.]+)",
        r"(?:给|为)([^，。,.]+?)(?:生成|制作|做|设计|拍|出)",
        r"(?:生成|制作|做|设计|拍)([^，。,.]+?)的",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            product = match.group(1).strip()
            product = re.sub(r"^(一个|一张|一组|它的|这个|这款)", "", product).strip()
            if product and product not in {"它", "这个", "这款"}:
                return product
    return text.strip()[:40] or "bakery product"


def _detect_content_type(text: str) -> str:
    for keyword, content_type in CONTENT_TYPE_MAP:
        if keyword in text:
            return content_type
    return "daily_product_content"


def _detect_platforms(text: str) -> str:
    platforms = [value for keyword, value in PLATFORM_KEYWORDS.items() if keyword in text]
    return ",".join(dict.fromkeys(platforms)) if platforms else "xiaohongshu,douyin"


def _extract_visual_intent(text: str) -> str:
    patterns = [
        r"(?:生成|制作|做|设计|拍|出)(?:一张|一组|一个|它的|这个|这款)?([^，。,.]+?图)",
        r"(?:生成|制作|做|设计|拍|出)(?:一张|一组|一个|它的|这个|这款)?([^，。,.]+?海报)",
        r"(?:生成|制作|做|设计|拍|出)(?:一张|一组|一个|它的|这个|这款)?([^，。,.]+?封面)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            intent = match.group(1).strip()
            intent = re.sub(r"^(它的|这个|这款|一张|一组|一个)", "", intent).strip()
            if intent:
                return intent
    return ""


def parse_natural_request(text: str, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    overrides = overrides or {}
    product_name = overrides.get("product_name") or _extract_product(text)
    image_type = overrides.get("image_type") or "product_hero"
    image_style = overrides.get("image_style") or "realistic bakery product photography"
    content_type = overrides.get("content_type") or _detect_content_type(text)
    visual_intent = overrides.get("visual_intent") or _extract_visual_intent(text)

    for keyword, mapped_type, mapped_style in STYLE_MAP:
        if keyword in text:
            image_type = overrides.get("image_type") or mapped_type
            image_style = overrides.get("image_style") or mapped_style
            break

    return {
        "natural_request": text,
        "product_name": product_name,
        "content_type": content_type,
        "image_type": image_type,
        "image_style": image_style,
        "visual_intent": visual_intent,
        "platforms": overrides.get("platforms") or overrides.get("platform") or _detect_platforms(text),
        "campaign_goal": overrides.get("campaign_goal") or f"Generate review-ready title, copy, and multiple image prompts for: {text}. Skip video generation.",
        "audience": overrides.get("audience") or "local bakery customers and social media viewers",
        "constraints": overrides.get("constraints") or "No fake price, inventory, sales volume, health claims, nutrition claims, official authorization, logo, trademark, or embedded text.",
    }
