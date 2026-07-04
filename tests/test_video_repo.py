import pytest
from app.repositories.video_repo import VideoRepository

@pytest.mark.asyncio
async def test_create_and_get_video(db_session):
    repo = VideoRepository(db_session)
    video = await repo.create_video(filename="test.mp4")
    fetched = await repo.get_video(video.video_id)
    assert fetched.filename == "test.mp4"
    assert fetched.status == "pending"

@pytest.mark.asyncio
async def test_update_status(db_session):
    repo = VideoRepository(db_session)
    video = await repo.create_video(filename="test.mp4")
    await repo.update_status(video.video_id, "ready")
    fetched = await repo.get_video(video.video_id)
    assert fetched.status == "ready"

@pytest.mark.asyncio
async def test_mark_deleted(db_session):
    repo = VideoRepository(db_session)
    video = await repo.create_video(filename="test.mp4")
    await repo.mark_deleted(video.video_id)
    fetched = await repo.get_video(video.video_id)
    assert fetched.status == "deleted"

@pytest.mark.asyncio
async def test_deleted_status_is_not_overwritten(db_session):
    repo = VideoRepository(db_session)
    video = await repo.create_video(filename="test.mp4")
    await repo.mark_deleted(video.video_id)
    await repo.update_status(video.video_id, "ready")
    fetched = await repo.get_video(video.video_id)
    assert fetched.status == "deleted"
