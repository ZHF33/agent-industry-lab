import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_knowledge_dirs_exist():
    for rel in [
        "knowledge/raw",
        "knowledge/processed",
        "knowledge/standard",
        "knowledge/products",
        "knowledge/brand",
        "knowledge/customers",
        "knowledge/marketing",
        "knowledge/competitors",
        "knowledge/platforms",
        "knowledge/campaigns",
        "knowledge/templates",
    ]:
        assert (ROOT / rel).is_dir(), rel


def test_product_template_fields():
    text = (ROOT / "knowledge" / "standard" / "product_knowledge_template.md").read_text(encoding="utf-8")
    for field in ["产品名称", "产品类型", "价格", "原料", "卖点", "口感", "适合场景", "目标用户", "禁用表达", "备注"]:
        assert field in text


def test_json_schema_examples_are_valid():
    for path in (ROOT / "knowledge" / "templates").glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        for key in ["id", "type", "name", "tags", "source_file", "confidence", "fields", "todo"]:
            assert key in data, path
