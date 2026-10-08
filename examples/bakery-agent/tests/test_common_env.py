from services.common import load_dotenv


def test_load_dotenv_strips_utf8_bom(tmp_path):
    env = tmp_path / ".env"
    env.write_text("\ufeffMOCK_PUBLISH_ENABLED=true\nPUBLISH_CONNECTOR_MODE=mock\n", encoding="utf-8")

    values = load_dotenv(env)

    assert values["MOCK_PUBLISH_ENABLED"] == "true"
    assert "\ufeffMOCK_PUBLISH_ENABLED" not in values
