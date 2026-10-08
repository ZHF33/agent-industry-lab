def test_services_import():
    from services import approval_service, asset_service, campaign_service, db_service, db_sync_service, dify_client
    from services import image_generation_service, image_prompt_service, image_selection_service, image_service, knowledge_service, operation_log_service, publish_service, publisher_service, revision_service, task_service, video_service

    assert approval_service
    assert asset_service
    assert campaign_service
    assert db_service
    assert db_sync_service
    assert dify_client
    assert image_generation_service
    assert image_prompt_service
    assert image_selection_service
    assert image_service
    assert knowledge_service
    assert operation_log_service
    assert publish_service
    assert publisher_service
    assert revision_service
    assert task_service
    assert video_service
