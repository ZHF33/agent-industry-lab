from services import campaign_service, db_service


def test_campaign_create_update_summary(tmp_path):
    db = tmp_path / "ops.sqlite3"
    campaign = campaign_service.create_campaign({"campaign_name": "夏日奶茶内容", "product_name": "伯牙绝弦"}, db_path=db)
    assert campaign["campaign_id"].startswith("campaign_")
    updated = campaign_service.update_campaign_status(campaign["campaign_id"], "paused", db_path=db)
    assert updated["status"] == "paused"
    summary = campaign_service.summarize_campaign(campaign["campaign_id"], db_path=db)
    assert summary["run_count"] == 0


def test_attach_content_run_to_campaign(tmp_path):
    db = tmp_path / "ops.sqlite3"
    campaign = campaign_service.create_campaign({"campaign_name": "测试活动"}, db_path=db)
    with db_service.get_connection(db) as conn:
        db_service.upsert_content_run(conn, {"run_id": "run_test", "approval_status": "pending"})
    campaign_service.attach_content_run_to_campaign(campaign["campaign_id"], "run_test", db_path=db)
    summary = campaign_service.summarize_campaign(campaign["campaign_id"], db_path=db)
    assert summary["run_count"] == 1


def test_campaign_default_product_is_generic(tmp_path):
    db = tmp_path / "ops.sqlite3"
    campaign = campaign_service.create_campaign({"campaign_name": "Generic content"}, db_path=db)

    assert campaign["product_name"] == "bakery product"
