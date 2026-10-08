import json

import pytest
from pathlib import Path

from scripts import agent_http_api
from tests.test_generate_approved_images import make_approved_image_package
from tests.test_publish_service import make_publish_ready_package
from tests.test_update_approval_status import make_package


def test_agent_http_api_builds_safe_plain_request_command():
    request = "今日的爆品是牛肉恰巴塔，生成它的解构风展示图"
    command = agent_http_api._build_command(
        {
            "user_request": request,
            "execution_mode": "dry-run",
            "image_count": 3,
        }
    )
    assert command[0].endswith("python.exe") or command[0].endswith("python")
    assert "run_content_operation.py" in command[1]
    assert "--request" in command
    assert command[command.index("--request") + 1] == request
    assert " ".join(command).count(";") == 0


def test_agent_http_api_rejects_invalid_mode_and_image_count():
    with pytest.raises(ValueError):
        agent_http_api._build_command({"user_request": "test", "execution_mode": "shell"})
    with pytest.raises(ValueError):
        agent_http_api._build_command({"user_request": "test", "image_count": 20})
    with pytest.raises(ValueError):
        agent_http_api._build_command({"user_request": "test", "live_image": True})


def test_agent_http_api_authorization_is_required_when_token_configured(monkeypatch):
    class DummyHandler:
        headers = {}

    monkeypatch.delenv("AGENT_API_TOKEN", raising=False)
    monkeypatch.setattr(agent_http_api, "load_dotenv", lambda path=".env": {})
    assert agent_http_api._authorized(DummyHandler()) is False

    monkeypatch.setenv("AGENT_API_TOKEN", "secret")
    assert agent_http_api._authorized(DummyHandler()) is False

    class AuthorizedHandler:
        headers = {"Authorization": "Bearer secret"}

    assert agent_http_api._authorized(AuthorizedHandler()) is True


def test_agent_http_api_reads_token_from_dotenv(monkeypatch):
    class AuthorizedHandler:
        headers = {"Authorization": "Bearer dotenv-secret"}

    monkeypatch.delenv("AGENT_API_TOKEN", raising=False)
    monkeypatch.setattr(agent_http_api, "load_dotenv", lambda path=".env": {"AGENT_API_TOKEN": "dotenv-secret"})
    assert agent_http_api._authorized(AuthorizedHandler()) is True


def test_agent_http_api_updates_approval_status_and_syncs_db(tmp_path):
    package_dir = tmp_path / "approval_queue" / "run_api_review"
    db_path = tmp_path / "agent_ops.sqlite3"
    make_package(package_dir)

    result = agent_http_api.update_approval(
        {
            "package": str(package_dir),
            "status": "approved",
            "note": "人工确认图片可生成，文案待发布前复核。",
            "db": str(db_path),
        }
    )

    assert result["ok"] is True
    assert result["approval"]["status"] == "approved"
    assert result["approval"]["db_sync_status"] == "synced"


def test_agent_http_api_creates_revision_and_syncs_db(tmp_path):
    package_dir = tmp_path / "approval_queue" / "run_api_revision"
    db_path = tmp_path / "agent_ops.sqlite3"
    make_package(package_dir, status="needs_revision")

    result = agent_http_api.create_revision(
        {
            "package": str(package_dir),
            "note": "删除官方包装镜头。",
            "out_dir": str(tmp_path / "revisions"),
            "db": str(db_path),
        },
        timeout=10,
    )

    assert result["ok"] is True
    assert result["revision"]["approval_status"] == "pending_revision_review"
    assert result["revision"]["db_sync_status"] == "synced"


def test_agent_http_api_review_package_can_create_revision(tmp_path):
    package_dir = tmp_path / "approval_queue" / "run_api_review_revision"
    db_path = tmp_path / "agent_ops.sqlite3"
    make_package(package_dir)

    result = agent_http_api.review_package(
        {
            "package": str(package_dir),
            "status": "needs_revision",
            "note": "重写 CTA。",
            "create_revision": True,
            "out_dir": str(tmp_path / "revisions"),
            "db": str(db_path),
        },
        timeout=10,
    )

    assert result["ok"] is True
    assert result["approval"]["status"] == "needs_revision"
    assert result["revision"]["approval_status"] == "pending_revision_review"


def test_agent_http_api_generates_images_for_approved_package(tmp_path):
    package_dir = tmp_path / "approval_queue" / "run_api_image"
    db_path = tmp_path / "agent_ops.sqlite3"
    make_approved_image_package(package_dir)

    result = agent_http_api.generate_images(
        {
            "package": str(package_dir),
            "out_dir": str(tmp_path / "generated_images"),
            "db": str(db_path),
        }
    )

    assert result["ok"] is True
    assert result["image_generation"]["status"] == "prepared"
    assert result["image_generation"]["image_count"] == 2
    assert result["image_generation"]["db_sync_status"] == "synced"


def test_agent_http_api_generates_local_demo_images_for_approved_package(tmp_path):
    package_dir = tmp_path / "approval_queue" / "run_api_image_demo"
    db_path = tmp_path / "agent_ops.sqlite3"
    make_approved_image_package(package_dir)

    result = agent_http_api.generate_images(
        {
            "package": str(package_dir),
            "out_dir": str(tmp_path / "generated_images"),
            "db": str(db_path),
            "local_demo": True,
        }
    )

    assert result["ok"] is True
    assert result["image_generation"]["mode"] == "local_demo"
    assert result["image_generation"]["status"] == "completed"
    assert result["image_generation"]["image_paths"]


def test_agent_http_api_selects_image_variant(tmp_path):
    package_dir = tmp_path / "approval_queue" / "run_api_select_image"
    db_path = tmp_path / "agent_ops.sqlite3"
    make_approved_image_package(package_dir)
    agent_http_api.generate_images(
        {
            "package": str(package_dir),
            "out_dir": str(tmp_path / "generated_images"),
            "db": str(db_path),
            "local_demo": True,
        }
    )

    result = agent_http_api.select_image(
        {
            "package": str(package_dir),
            "image_id": "hero",
            "note": "Selected through Agent API.",
            "db": str(db_path),
        }
    )

    assert result["ok"] is True
    assert result["image_selection"]["image_id"] == "hero"
    assert result["image_selection"]["selected_image"]["review_status"] == "selected"


def test_agent_http_api_rejects_live_and_local_demo_together(tmp_path):
    package_dir = tmp_path / "approval_queue" / "run_api_image_mode_conflict"
    make_approved_image_package(package_dir)

    with pytest.raises(ValueError, match="cannot both be true"):
        agent_http_api.generate_images({"package": str(package_dir), "live": True, "local_demo": True})


def test_agent_http_api_live_image_gate_reads_dotenv(tmp_path, monkeypatch):
    package_dir = tmp_path / "approval_queue" / "run_api_image_dotenv_gate"
    env = tmp_path / ".env"
    make_approved_image_package(package_dir)
    env.write_text("AGENT_API_ALLOW_LIVE_IMAGE=true\n", encoding="utf-8")
    monkeypatch.delenv("AGENT_API_ALLOW_LIVE_IMAGE", raising=False)
    monkeypatch.setattr(agent_http_api.image_generation_service, "generate_for_package", lambda *args, **kwargs: {
        "ok": False,
        "image_generation": {"status": "failed"},
        "package_dir": str(package_dir),
        "run_id": package_dir.name,
        "approval_status": "approved",
        "db_sync_status": "skipped",
        "db": str(tmp_path / "agent_ops.sqlite3"),
        "error": "provider not called in unit test",
    })

    result = agent_http_api.generate_images(
        {
            "package": str(package_dir),
            "live": True,
            "env_file": str(env),
            "db": str(tmp_path / "agent_ops.sqlite3"),
        }
    )

    assert result["ok"] is False
    assert result["error"] == "provider not called in unit test"


def test_agent_http_api_prepares_publish_draft(tmp_path):
    package_dir, _output = make_publish_ready_package(tmp_path)
    db_path = tmp_path / "agent_ops.sqlite3"

    result = agent_http_api.prepare_publish_draft(
        {
            "package": str(package_dir),
            "out_dir": str(tmp_path / "publish_drafts"),
            "db": str(db_path),
        }
    )

    assert result["ok"] is True
    assert result["publish_draft"]["status"] == "draft_prepared"
    assert result["publish_draft"]["selected_image_id"] == "cutaway_detail"
    assert Path(result["publish_draft"]["package_draft_path"]).exists()


def test_agent_http_api_records_manual_publish(tmp_path):
    package_dir, _output = make_publish_ready_package(tmp_path)
    db_path = tmp_path / "agent_ops.sqlite3"
    agent_http_api.prepare_publish_draft({"package": str(package_dir), "out_dir": str(tmp_path / "publish_drafts"), "db": str(db_path)})

    result = agent_http_api.record_publish(
        {
            "package": str(package_dir),
            "platform": "xiaohongshu",
            "published_url": "https://example.com/xhs/1",
            "note": "Manual publish recorded via API.",
            "metrics": {"likes": 7},
            "db": str(db_path),
        }
    )

    assert result["ok"] is True
    assert result["publish_record"]["status"] == "partially_published"
    assert result["publish_record"]["platform"] == "xiaohongshu"
    assert result["publish_record"]["pending_platforms"] == ["douyin"]

    second = agent_http_api.record_publish(
        {
            "package": str(package_dir),
            "platform": "douyin",
            "published_url": "https://example.com/douyin/1",
            "note": "Manual publish recorded via API.",
            "metrics": {"likes": 3},
            "db": str(db_path),
        }
    )

    assert second["ok"] is True
    assert second["publish_record"]["status"] == "published"
    assert second["publish_record"]["pending_platforms"] == []


def test_agent_http_api_mock_publish(tmp_path):
    package_dir, _output = make_publish_ready_package(tmp_path)
    db_path = tmp_path / "agent_ops.sqlite3"
    env = tmp_path / ".env"
    env.write_text("MOCK_PUBLISH_ENABLED=true\nPUBLISH_CONNECTOR_MODE=mock\n", encoding="utf-8")
    agent_http_api.prepare_publish_draft({"package": str(package_dir), "out_dir": str(tmp_path / "publish_drafts"), "db": str(db_path)})

    result = agent_http_api.mock_publish(
        {
            "package": str(package_dir),
            "platform": "xiaohongshu",
            "db": str(db_path),
            "env_file": str(env),
        }
    )

    assert result["ok"] is True
    assert result["mock_publish"]["mode"] == "mock"
    assert result["mock_publish"]["publish_record"]["platform"] == "xiaohongshu"


def test_agent_http_api_pipeline_defaults_to_manual_publish_records(tmp_path, monkeypatch):
    package_dir = tmp_path / "approval_queue" / "run_pipeline_default_publish"
    package_dir.mkdir(parents=True)
    metadata = {
        "run_id": package_dir.name,
        "status": "pending",
        "approval_status": "pending",
        "product_name": "草莓拿破仑",
        "platform": "xiaohongshu,douyin",
        "assets": {"image_generation": {"images": [{"image_id": "hero"}]}},
    }
    (package_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")
    publish_records = []
    approval_payloads = []

    monkeypatch.setattr(agent_http_api, "run_operation", lambda payload, timeout: {
        "ok": True,
        "operation": {"approval_package": str(package_dir), "content_task": {"product_name": "草莓拿破仑"}},
    })
    monkeypatch.setattr(agent_http_api, "update_approval", lambda payload: (_ for _ in ()).throw(AssertionError("update_approval should not be called in manual approval mode")))
    monkeypatch.setattr(agent_http_api, "generate_images", lambda payload: (_ for _ in ()).throw(AssertionError("generate_images should not be called in manual approval mode")))
    monkeypatch.setattr(agent_http_api, "select_image", lambda payload: (_ for _ in ()).throw(AssertionError("select_image should not be called in manual approval mode")))
    monkeypatch.setattr(agent_http_api, "prepare_publish_draft", lambda payload: (_ for _ in ()).throw(AssertionError("prepare_publish_draft should not be called in manual approval mode")))
    monkeypatch.setattr(agent_http_api, "record_publish", lambda payload: (_ for _ in ()).throw(AssertionError("record_publish should not be called in manual approval mode")))
    monkeypatch.setattr(agent_http_api, "mock_publish", lambda payload: (_ for _ in ()).throw(AssertionError("mock_publish should not be called by default")))

    result = agent_http_api.run_pipeline(
        {"user_request": "今日新品是草莓拿破仑，生成它的下午茶场景图", "preferred_image_id": "hero"},
        timeout=10,
    )

    assert result["ok"] is True
    assert result["stage"] == "pending_approval"
    assert result["approval_required"] is True
    assert result["approval"]["status"] == "pending"
    assert result["next_action"]["action"] == "human_review"


def test_agent_http_api_pipeline_auto_approve_runs_publish_chain(tmp_path, monkeypatch):
    package_dir = tmp_path / "approval_queue" / "run_pipeline_auto_publish"
    package_dir.mkdir(parents=True)
    metadata = {
        "run_id": package_dir.name,
        "status": "pending",
        "approval_status": "pending",
        "product_name": "草莓拿破仑",
        "platform": "xiaohongshu,douyin",
        "assets": {"image_generation": {"images": [{"image_id": "hero"}]}},
    }
    (package_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")
    publish_records = []
    approval_payloads = []

    monkeypatch.setattr(agent_http_api, "run_operation", lambda payload, timeout: {
        "ok": True,
        "operation": {"approval_package": str(package_dir), "content_task": {"product_name": "草莓拿破仑"}},
    })
    def fake_update_approval(payload):
        approval_payloads.append(payload)
        return {"approval": {"status": "approved", "package_dir": str(package_dir)}}

    monkeypatch.setattr(agent_http_api, "update_approval", fake_update_approval)
    monkeypatch.setattr(agent_http_api, "generate_images", lambda payload: {"image_generation": {"status": "completed"}})
    monkeypatch.setattr(agent_http_api, "select_image", lambda payload: {"image_selection": {"image_id": payload["image_id"]}})
    monkeypatch.setattr(agent_http_api, "prepare_publish_draft", lambda payload: {"publish_draft": {"status": "draft_prepared"}})

    def fake_record_publish(payload):
        record = {"platform": payload["platform"], "status": "published", "note": payload["note"]}
        publish_records.append(record)
        current = json.loads((package_dir / "metadata.json").read_text(encoding="utf-8"))
        current["publish_status"] = "published"
        current["publish_records"] = publish_records
        current["selected_image_id"] = "hero"
        current["image_status"] = "completed"
        current["approval_status"] = "approved"
        (package_dir / "metadata.json").write_text(json.dumps(current, ensure_ascii=False), encoding="utf-8")
        return {"publish_record": record}

    monkeypatch.setattr(agent_http_api, "record_publish", fake_record_publish)
    monkeypatch.setattr(agent_http_api, "mock_publish", lambda payload: (_ for _ in ()).throw(AssertionError("mock_publish should not be called by default")))

    result = agent_http_api.run_pipeline(
        {"user_request": "今日新品是草莓拿破仑，生成它的下午茶场景图", "preferred_image_id": "hero", "auto_approve": True},
        timeout=10,
    )

    assert result["ok"] is True
    assert result["mock_publish_results"] == []
    assert approval_payloads[0]["note"] == "Pipeline auto-approved because approval_mode=auto was explicitly requested."
    assert [record["platform"] for record in result["publish_records"]] == ["xiaohongshu", "douyin"]
    assert all("placeholder" not in record["note"].lower() for record in result["publish_records"])
    assert all("operator-owned" in record["note"] for record in result["publish_records"])


def test_agent_http_api_rejects_unapproved_image_generation(tmp_path):
    package_dir = tmp_path / "approval_queue" / "run_api_image_pending"
    make_approved_image_package(package_dir, status="pending")

    with pytest.raises(ValueError, match="requires approved package status"):
        agent_http_api.generate_images({"package": str(package_dir)})


def test_agent_http_api_rejects_large_image_generation_batch(tmp_path):
    package_dir = tmp_path / "approval_queue" / "run_api_image_too_many"
    make_approved_image_package(package_dir)

    with pytest.raises(ValueError, match="n must be between 1 and 8"):
        agent_http_api.generate_images({"package": str(package_dir), "n": 9})


def test_agent_http_api_records_image_failure(tmp_path, monkeypatch):
    package_dir = tmp_path / "approval_queue" / "run_api_image_failure"
    db_path = tmp_path / "agent_ops.sqlite3"
    make_approved_image_package(package_dir)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("AGENT_API_ALLOW_LIVE_IMAGE", "true")
    monkeypatch.setattr(agent_http_api.image_service, "load_dotenv", lambda path=".env": {})

    result = agent_http_api.generate_images(
        {
            "package": str(package_dir),
            "out_dir": str(tmp_path / "generated_images"),
            "live": True,
            "require_key": True,
            "db": str(db_path),
        }
    )

    assert result["ok"] is False
    assert result["image_generation"]["status"] == "failed"
    assert "OPENAI_API_KEY is required" in result["error"]


def test_agent_http_api_does_not_allow_unapproved_image_bypass(tmp_path):
    package_dir = tmp_path / "approval_queue" / "run_api_image_pending_bypass"
    make_approved_image_package(package_dir, status="pending")

    with pytest.raises(ValueError, match="requires approved package status"):
        agent_http_api.generate_images({"package": str(package_dir), "allow_unapproved": True})


def test_agent_http_api_rejects_paths_outside_workspace(tmp_path):
    outside = Path("C:/Windows/System32/not-a-package")

    with pytest.raises(ValueError, match="workspace root"):
        agent_http_api.generate_images({"package": str(outside)})


def test_agent_http_api_image_readiness_payload():
    readiness = agent_http_api.image_service.live_image_readiness(require_agent_api_allow=True)
    assert "ready" in readiness
    assert "blockers" in readiness
    assert readiness["provider"] == "openai"
