from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_required_top_level_files_exist():
    for rel in ["README.md", ".env.example", "docker-compose.yml", "configs/agent_config.yml"]:
        assert (ROOT / rel).exists(), rel


def test_env_example_has_required_keys():
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    for key in [
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
        "OPENAI_MODEL",
        "OPENAI_TIMEOUT_SECONDS",
        "OPENAI_IMAGE_MODEL",
        "OPENAI_IMAGE_SIZE",
        "OPENAI_IMAGE_QUALITY",
        "ANTHROPIC_API_KEY",
        "SEEDANCE_API_KEY",
        "KLING_API_KEY",
        "DIFY_API_KEY",
        "DIFY_BASE_URL",
        "N8N_BASE_URL",
        "AGENT_API_URL",
        "AGENT_API_ALLOW_LIVE_IMAGE",
        "AGENT_API_TOKEN",
        "FEISHU_APP_ID",
        "FEISHU_APP_SECRET",
    ]:
        assert f"{key}=" in text
