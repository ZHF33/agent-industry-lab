import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_normalize_and_build_index_with_sample_product():
    raw_dir = ROOT / "knowledge" / "raw"
    processed_dir = ROOT / "knowledge" / "processed"
    sample = raw_dir / "pytest_hokkaido_toast.md"
    outputs = [
        processed_dir / "pytest_hokkaido_toast.standard.md",
        processed_dir / "pytest_hokkaido_toast.json",
        ROOT / "knowledge" / "products" / "pytest_hokkaido_toast.json",
        processed_dir / "knowledge_index.json",
    ]

    for path in outputs:
        if path.exists():
            path.unlink()

    sample.write_text(
        "\n".join(
            [
                "产品名称: 北海道吐司",
                "产品类型: 吐司",
                "价格: 39",
                "原料: 牛奶、面粉、黄油",
                "卖点: 奶香浓郁、适合早餐",
                "口感: 柔软微甜",
                "适合场景: 早餐、儿童加餐",
                "目标用户: 家庭用户、宝妈",
                "禁用表达: 治疗、减肥",
            ]
        ),
        encoding="utf-8",
    )

    try:
        subprocess.run([sys.executable, "scripts/normalize_knowledge.py"], cwd=ROOT, check=True)
        subprocess.run([sys.executable, "scripts/build_knowledge_index.py"], cwd=ROOT, check=True)

        record = json.loads((processed_dir / "pytest_hokkaido_toast.json").read_text(encoding="utf-8"))
        assert record["type"] == "product"
        assert record["name"] == "北海道吐司"
        assert record["price"] == 39
        assert "早餐" in record["tags"]
        assert record["fields"]["ingredients"] == ["牛奶", "面粉", "黄油"]

        index = json.loads((processed_dir / "knowledge_index.json").read_text(encoding="utf-8"))
        assert "product_pytest_hokkaido_toast" in index["by_type"]["product"]
    finally:
        if sample.exists():
            sample.unlink()
        for path in outputs:
            if path.exists():
                path.unlink()
