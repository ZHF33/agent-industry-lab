"""Decode, validate and re-encode synthetic meter records."""
import json


def review(raw):
    try:
        record = json.loads(raw)
    except json.JSONDecodeError:
        return {"status": "syntax_error"}
    if not isinstance(record, dict) or type(record.get("wh")) is not int or record["wh"] < 0:
        return {"status": "contract_error"}
    return {"status": "accepted", "wh": record["wh"]}


if __name__ == "__main__":
    samples = ('{"wh": 500}', '{"wh": "500"}', '{"wh": 500,}')
    for raw in samples:
        print(json.dumps(review(raw), sort_keys=True))
