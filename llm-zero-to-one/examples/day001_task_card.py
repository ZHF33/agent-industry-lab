"""Original fixed teaching task card; no model or external service calls."""
from decimal import Decimal


def main():
    unit_price = Decimal("8.50")
    quantity = 12
    total = unit_price * quantity
    print("任务：生成商品介绍草稿")
    print("已知：产品、价格、配料、过敏原")
    print("缺失：含糖量检测、健康适用结论")
    print(f"12个合计：{total:.2f}元")
    print("发布权限：需人工另行授权")


if __name__ == "__main__":
    main()
