"""Offline queue-state illustration. Not a durable broker or business processor."""
from collections import deque


def main():
    ready = deque(["JOB-DEMO-01", "JOB-DEMO-02"])
    unacked = {}
    delivered = ready.popleft()
    unacked[1] = delivered
    print("after_delivery:", len(ready), len(unacked))
    # Simulate connection loss: delivery returns to the ready collection.
    ready.appendleft(unacked.pop(1))
    print("after_redelivery:", list(ready))
    again = ready.popleft()
    unacked[2] = again
    unacked.pop(2)  # Acknowledgement in this teaching model.
    print("after_ack:", len(ready), len(unacked))
    print("business_effects_verified:", False)


if __name__ == "__main__":
    main()
