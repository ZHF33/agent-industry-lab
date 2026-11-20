"""Compare default JSON decoding with a duplicate-key check."""
import json


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate {key}")
        result[key] = value
    return result


if __name__ == "__main__":
    for sample in ('{"slots":{"peak":500}}', '{"slots":{"peak":0,"peak":500}}'):
        print("default", json.loads(sample)["slots"]["peak"])
        try:
            result = json.loads(sample, object_pairs_hook=unique_object)
            print("checked", result["slots"]["peak"])
        except ValueError as error:
            print("rejected", error)
