"""Report malformed input while letting unrelated bugs surface."""
import json
import sys


def decode_booking(raw):
    return json.loads(raw)


def review_line(raw):
    try:
        booking = decode_booking(raw)
    except json.JSONDecodeError as error:
        return f"invalid_json line={error.lineno} column={error.colno}"
    return f"decoded {booking['id']}"


if __name__ == "__main__":
    if sys.argv[1:] == ["--traceback"]:
        decode_booking("{")
    else:
        for record in ('{"id":"A"}', "{"):
            print(review_line(record))
