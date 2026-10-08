import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_gpt_readiness_config_check_passes_without_key():
    result = subprocess.run(
        [sys.executable, "scripts/check_gpt_readiness.py"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert '"provider": "openai"' in result.stdout
    assert '"dify_dsl_ready": true' in result.stdout


def test_stage_1_2_models_are_openai_first():
    text = (ROOT / "configs" / "models.example.yml").read_text(encoding="utf-8")
    assert "planner:" in text
    assert "provider: openai" in text
    assert "enabled_in_stage_1_2: false" in text


def test_image_readiness_can_require_ready():
    result = subprocess.run(
        [sys.executable, "scripts/check_image_readiness.py", "--require-ready", "--require-agent-api-allow"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert '"provider": "openai"' in result.stdout
    assert '"blockers":' in result.stdout
    assert result.returncode in {0, 1}
