from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLAIN_REQUEST = "今日的爆品是牛肉恰巴塔，生成它的解构风展示图"
PRODUCT_NAME = "牛肉恰巴塔"


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_core_plain_request_examples_are_valid_utf8():
    for rel in [
        "README.md",
        "tests/test_content_request_service.py",
        "tests/test_v2_operation.py",
        "docs/operation_archive.md",
    ]:
        text = read(rel)
        assert PLAIN_REQUEST in text or PRODUCT_NAME in text, rel
    parser = read("services/content_request_service.py")
    for keyword in ["爆品", "产品", "生成", "解构", "展示图"]:
        assert keyword in parser


def test_common_mojibake_fragments_are_absent_from_user_facing_sources():
    forbidden = ["ä»Š", "çˆ†", "ç‰›", "è§£", "ï¼Œ", "ã€‚"]
    for rel in [
        "README.md",
        "docs/operation_archive.md",
        "docs/changelog.md",
        "tests/test_content_request_service.py",
        "tests/test_v2_operation.py",
        "services/content_request_service.py",
    ]:
        text = read(rel)
        for fragment in forbidden:
            assert fragment not in text, f"{rel} contains mojibake fragment {fragment!r}"
