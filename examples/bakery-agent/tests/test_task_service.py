from services import task_service


def test_task_lifecycle(tmp_path):
    db = tmp_path / "ops.sqlite3"
    task = task_service.create_task("image_generation", provider="openai", input_json={"x": 1}, db_path=db)
    assert task["status"] == "pending"
    updated = task_service.update_task_status(task["task_id"], "succeeded", output_json={"ok": True}, db_path=db)
    assert updated["status"] == "succeeded"
    assert task_service.get_task(task["task_id"], db_path=db)["task_type"] == "image_generation"


def test_list_pending_tasks(tmp_path):
    db = tmp_path / "ops.sqlite3"
    task_service.create_task("db_sync", db_path=db)
    assert len(task_service.list_pending_tasks(db_path=db)) == 1


def test_task_links(tmp_path):
    db = tmp_path / "ops.sqlite3"
    task = task_service.create_task("approval_review", db_path=db)
    task_service.link_task_to_approval_package(task["task_id"], "runs/approval_queue/run_test", db_path=db)
    linked = task_service.link_task_to_asset(task["task_id"], "asset_test", db_path=db)
    assert linked["related_package_path"]
    assert linked["related_asset_id"] == "asset_test"

