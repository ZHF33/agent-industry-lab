"""Manual exercise confined to a new temporary synthetic workspace."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory


if __name__ == "__main__":
    with TemporaryDirectory(prefix="llm-file-lesson-") as directory:
        root = Path(directory)
        inputs = root / "inputs"
        outputs = root / "outputs"
        inputs.mkdir()
        outputs.mkdir()
        sample = inputs / "sample.json"
        sample.write_text(json.dumps({"export_id": "EXPORT-DEMO-A"}), encoding="utf-8")
        print("folders:", sorted(path.name for path in root.iterdir()))
        print("file:", sample.name)
        print("suffix:", sample.suffix)
        print("parent:", sample.parent.name)
        print("record:", json.loads(sample.read_text(encoding="utf-8"))["export_id"])
        print("missing exists:", (inputs / "missing.json").exists())
