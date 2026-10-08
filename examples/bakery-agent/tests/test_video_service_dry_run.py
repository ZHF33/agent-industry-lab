from services import video_service


def test_video_service_dry_run_task():
    task = video_service.create_video_task({"scene": "tea"}, provider="kling", dry_run=True)
    assert task["status"] == "created_placeholder"
    polled = video_service.poll_video_task(task)
    assert polled["status"] == "completed_placeholder"

