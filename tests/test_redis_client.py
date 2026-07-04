import pytest
from app.clients.redis_client import(
    set_chunk_total,
    increment_completed,
    get_progress,
    is_transcoding_complete,
    cleanup_progress,
)

TEST_VIDEO_ID = "test_video_id"
TEST_RESOLUTION = "720p"

@pytest.fixture(autouse=True)
async def cleanup_before_and_after():
    await cleanup_progress(TEST_VIDEO_ID, TEST_RESOLUTION)
    yield
    await cleanup_progress(TEST_VIDEO_ID, TEST_RESOLUTION)

async def test_set_and_get_progress():
    await set_chunk_total(TEST_VIDEO_ID, TEST_RESOLUTION, 10)
    completed, total = await get_progress(TEST_VIDEO_ID, TEST_RESOLUTION)
    assert completed == 0
    assert total == 10

async def test_increment_completed():
    await set_chunk_total(TEST_VIDEO_ID, TEST_RESOLUTION, total=5)
    await increment_completed(TEST_VIDEO_ID, TEST_RESOLUTION)
    await increment_completed(TEST_VIDEO_ID, TEST_RESOLUTION)
    completed, total = await get_progress(TEST_VIDEO_ID, TEST_RESOLUTION)
    assert completed == 2
    assert total == 5


async def test_is_transcoding_complete_false_when_partial():
    await set_chunk_total(TEST_VIDEO_ID, TEST_RESOLUTION, total=3)
    await increment_completed(TEST_VIDEO_ID, TEST_RESOLUTION)
    assert await is_transcoding_complete(TEST_VIDEO_ID, TEST_RESOLUTION) is False


async def test_is_transcoding_complete_true_when_all_done():
    await set_chunk_total(TEST_VIDEO_ID, TEST_RESOLUTION, total=2)
    await increment_completed(TEST_VIDEO_ID, TEST_RESOLUTION)
    await increment_completed(TEST_VIDEO_ID, TEST_RESOLUTION)
    assert await is_transcoding_complete(TEST_VIDEO_ID, TEST_RESOLUTION) is True


async def test_is_transcoding_complete_false_when_no_total_set():
    assert await is_transcoding_complete(TEST_VIDEO_ID, TEST_RESOLUTION) is False


async def test_cleanup_progress_removes_keys():
    await set_chunk_total(TEST_VIDEO_ID, TEST_RESOLUTION, total=5)
    await increment_completed(TEST_VIDEO_ID, TEST_RESOLUTION)
    await cleanup_progress(TEST_VIDEO_ID, TEST_RESOLUTION)
    completed, total = await get_progress(TEST_VIDEO_ID, TEST_RESOLUTION)
    assert completed == 0
    assert total == 0