from services import content_request_service


def test_parse_plain_chinese_best_seller_request():
    task = content_request_service.parse_natural_request("今日的爆品是牛肉恰巴塔，生成它的解构风展示图")
    assert task["product_name"] == "牛肉恰巴塔"
    assert task["content_type"] == "best_seller_feature"
    assert task["image_type"] == "deconstructed_exploded_view"
    assert "deconstructed" in task["image_style"]
    assert task["platforms"] == "xiaohongshu,douyin"
    assert "health claims" in task["constraints"]


def test_parse_multiple_product_and_image_style_requests():
    cases = [
        ("给开心果可颂做小红书切面特写", "开心果可颂", "cutaway_detail", "daily_product_content", "xiaohongshu"),
        ("新品是草莓拿破仑，制作一组下午茶场景图", "草莓拿破仑", "lifestyle_scene", "new_product_launch", "xiaohongshu,douyin"),
        ("本周主推黑芝麻贝果，生成抖音封面", "黑芝麻贝果", "short_video_cover", "featured_product", "douyin"),
        ("为巧克力布里欧修拍细节海报", "巧克力布里欧修", "texture_closeup", "daily_product_content", "xiaohongshu,douyin"),
    ]

    for request, product, image_type, content_type, platforms in cases:
        task = content_request_service.parse_natural_request(request)
        assert task["product_name"] == product
        assert task["image_type"] == image_type
        assert task["content_type"] == content_type
        assert task["platforms"] == platforms


def test_parse_request_respects_structured_overrides():
    task = content_request_service.parse_natural_request(
        "新品是草莓拿破仑，制作一组下午茶场景图",
        {"product_name": "蓝莓丹麦", "image_type": "product_hero", "platform": "wechat_channels"},
    )

    assert task["product_name"] == "蓝莓丹麦"
    assert task["image_type"] == "product_hero"
    assert task["platforms"] == "wechat_channels"


def test_parse_request_preserves_unknown_visual_intent():
    request = "\u4eca\u65e5\u7684\u7206\u54c1\u662f\u67e0\u6aac\u53ef\u9882\uff0c\u751f\u6210\u5b83\u7684\u4f4e\u9971\u548c\u6742\u5fd7\u98ce\u9648\u5217\u56fe"
    task = content_request_service.parse_natural_request(request)

    assert task["product_name"] == "\u67e0\u6aac\u53ef\u9882"
    assert task["image_type"] == "product_hero"
    assert task["visual_intent"] == "\u4f4e\u9971\u548c\u6742\u5fd7\u98ce\u9648\u5217\u56fe"
    assert "\u4f4e\u9971\u548c\u6742\u5fd7\u98ce\u9648\u5217\u56fe" in task["campaign_goal"]
