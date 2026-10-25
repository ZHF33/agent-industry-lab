"""Offline snapshot/TTL comparison; no Redis, cache deletion or price writes."""
import copy
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "examples" / "product-cache-review"))
from agent import PRODUCTS, assess


def main():
    record = copy.deepcopy(PRODUCTS["PRODUCT-DEMO-01"])
    result = assess(record, "2026-10-24T11:05:00+00:00")
    for key in ["projected_remaining_ttl_seconds", "origin_version_match", "cache_minus_origin_price", "current_cache_presence"]:
        print(f"{key}: {result[key]}")
    # Change only the source version in the cache; equal versions alone don't fix data.
    record["cache"]["origin_version"] = "v2"
    changed = assess(record, "2026-10-24T11:05:00+00:00")
    print("version_label_fixed_but_price_difference:", changed["cache_minus_origin_price"])


if __name__ == "__main__":
    main()
