import subprocess
import sys

ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]


def test_init_local_db_cli_wrapper(tmp_path):
    db = tmp_path / "ops.sqlite3"
    subprocess.run([sys.executable, "scripts/init_local_db.py", "--db", str(db)], cwd=ROOT, check=True)
    assert db.exists()


def test_generate_openai_image_cli_dry_run(tmp_path):
    prompt = tmp_path / "prompt.json"
    prompt.write_text('{"enhanced_prompt_en":"unbranded tea"}', encoding="utf-8")
    out = tmp_path / "images"
    subprocess.run([sys.executable, "scripts/generate_openai_image.py", "--input", str(prompt), "--out-dir", str(out)], cwd=ROOT, check=True)
    assert list(out.glob("*.json"))

