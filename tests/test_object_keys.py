from app.workers.assembler import assemble_video
from app.clients.minio_client import BUCKET

def test_assembled_key_format():
    video_id = "abc-123"
    resolution = "720p"
    expected_key = f"{video_id}_{resolution}.mp4"
