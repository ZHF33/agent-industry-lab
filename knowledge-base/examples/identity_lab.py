if __name__ == "__main__":
    order = {"po_id": "PO-DEMO-01", "sku": "ITEM-A"}
    receipt = {"po_id": "PO-DEMO-01", "sku": "ITEM-B"}
    print("same_order", order["po_id"] == receipt["po_id"])
    print("same_item", order["sku"] == receipt["sku"])
