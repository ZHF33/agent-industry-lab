from collections import Counter


if __name__ == "__main__":
    deliveries = [("E-1", "timeout"), ("E-1", "timeout"), ("E-2", "timeout"), ("E-3", "queue")]
    unique = dict(deliveries)  # Teaching example assumes no conflicting payloads.
    counts = Counter(unique.values())
    print("deliveries", len(deliveries))
    print("unique_events", len(unique))
    print("timeout_events", counts["timeout"])
