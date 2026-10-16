"""Content fingerprint example, not authenticity verification."""
import hashlib


def fingerprint(value):
    return hashlib.sha256(value).hexdigest()


if __name__ == "__main__":
    original = b"demo-A"
    copied = b"demo-A"
    changed = b"demo-B"
    print("same_content", fingerprint(original) == fingerprint(copied))
    print("changed_content", fingerprint(original) == fingerprint(changed))
    print("same_size", len(original) == len(changed))
