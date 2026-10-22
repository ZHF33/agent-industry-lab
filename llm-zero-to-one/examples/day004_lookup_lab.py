"""Toy learned estimate versus authoritative keyed lookup. Not an LLM."""
from decimal import Decimal


def estimate(feature, weight):
    return feature * weight


def main():
    feature = Decimal("2")
    weight = Decimal("4")
    documents = {"SKU-DEMO-01": {"price": "8.50", "source": "approved-card-v1"}}
    print("toy_estimate:", estimate(feature, weight))
    print("lookup_v1:", documents["SKU-DEMO-01"]["price"])
    documents["SKU-DEMO-01"] = {"price": "9.00", "source": "approved-card-v2"}
    print("lookup_v2:", documents["SKU-DEMO-01"]["price"])
    print("weight_after_document_update:", weight)
    print("estimate_after_document_update:", estimate(feature, weight))
    print("missing_record:", documents.get("SKU-NOT-PROVIDED", "not_found"))


if __name__ == "__main__":
    main()
