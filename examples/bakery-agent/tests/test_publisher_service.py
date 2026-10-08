import json
import subprocess
import sys
from pathlib import Path

from services import publish_service, publisher_service
from tests.test_publish_service import make_publish_ready_package


ROOT = Path(__file__).resolve().parents[1]


def test_connector_readiness_reports_manual_mock_and_live_blockers(tmp_path):
    env = tmp_path / ".env"
    env.write_text("PUBLISH_CONNECTOR_MODE=mock\nMOCK_PUBLISH_ENABLED=true\n", encoding="utf-8")

    report = publisher_service.connector_readiness(env, ["xiaohongshu", "douyin"])

    assert report["manual_record_ready"] is True
    assert report["mock_ready"] is True
    assert report["live_ready"] is False
    assert report["platforms"]["xiaohongshu"]["mock_ready"] is True
    assert "Live publisher implementation is not connected yet" in report["platforms"]["douyin"]["blockers"][-1]


def test_mock_publish_records_platform_result(tmp_path):
    package_dir, _output = make_publish_ready_package(tmp_path)
    db = tmp_path / "ops.sqlite3"
    env = tmp_path / ".env"
    env.write_text("PUBLISH_CONNECTOR_MODE=mock\nMOCK_PUBLISH_ENABLED=true\n", encoding="utf-8")
    publish_service.prepare_publish_draft(package_dir, out_dir=tmp_path / "drafts", db=db)

    result = publisher_service.mock_publish(package_dir, platform="xiaohongshu", db=db, env_file=env)

    assert result["mode"] == "mock"
    assert result["mock_url"].startswith("https://mock.local/xiaohongshu/")
    assert result["publish_record"]["status"] == "partially_published"
    metadata = json.loads((package_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["publish_records"][0]["platform"] == "xiaohongshu"
    assert metadata["publish_records"][0]["published_url"] == result["mock_url"]


def test_mock_publish_requires_explicit_enable(tmp_path):
    package_dir, _output = make_publish_ready_package(tmp_path)
    publish_service.prepare_publish_draft(package_dir, out_dir=tmp_path / "drafts", db=tmp_path / "ops.sqlite3")

    try:
        publisher_service.mock_publish(package_dir, platform="xiaohongshu", env_file=tmp_path / "missing.env")
    except RuntimeError as exc:
        assert "Mock publish is disabled" in str(exc)
    else:
        raise AssertionError("Expected mock publish to require explicit enable.")


def test_check_publish_readiness_cli(tmp_path):
    env = tmp_path / ".env"
    env.write_text("PUBLISH_CONNECTOR_MODE=manual\nMOCK_PUBLISH_ENABLED=false\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/check_publish_readiness.py",
            "--env-file",
            str(env),
            "--json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )

    data = json.loads(result.stdout)
    assert data["manual_record_ready"] is True
    assert data["live_ready"] is False
