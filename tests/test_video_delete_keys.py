import os
import uuid


os.environ.setdefault("MINIO_BUCKET", "heavenlake")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://heavenlake:heavenlake@postgres:5432/heavenlake")

os.environ["MINIO_ENDPOINT"]
os.environ["MINIO_ACCESS_KEY"]
os.environ["MINIO_SECRET_KEY"]


from app.api.endpoints.videos import TARGET_RESOLUTIONS, video_storage_keys


def test_video_storage_keys_include_original_resolutions_and_chunks():
    video_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

    keys = video_storage_keys(video_id, chunk_count=2)

    assert f"{video_id}.mp4" in keys
    for resolution in TARGET_RESOLUTIONS:
        assert f"{video_id}_{resolution}.mp4" in keys

    for chunk_index in range(2):
        assert f"{video_id}_{chunk_index}.mp4" in keys
        for resolution in TARGET_RESOLUTIONS:
            assert f"{video_id}_{chunk_index}_{resolution}.mp4" in keys
