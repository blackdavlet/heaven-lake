import os
import subprocess
from app.clients.minio_client import upload_file, download_file

def split_video(video_id: str, chunk_duration_sec: int = 5) -> list[str]:
    object_key = f"{video_id}.mp4"
    local_input = f"/tmp/{video_id}_original.mp4"
    local_audio_path = f"/tmp/{video_id}_audio.aac"
    local_chunk_dir = f"/tmp/{video_id}_chunks"
    os.makedirs(local_chunk_dir, exist_ok=True)

    download_file(object_key, local_input)
    """
    cmd = [
        "ffmpeg", "-y", "-i", local_input,
        "-f", "segment",
        "-segment_time", str(chunk_duration_sec),
        "-c", "copy",
        "-reset_timestamps", "1",
        os.path.join(local_chunk_dir, "chunk_%03d.mp4")
    ]
    """
    audio_cmd = [
        "ffmpeg", "-y", "-i", local_input,
        "-vn", "-c:a", "aac", "-b:a", "128k",
        local_audio_path
    ]

    subprocess.run(audio_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    cmd = [
        "ffmpeg", "-y", "-i", local_input,
        "-f", "segment",
        "-segment_time", str(chunk_duration_sec),
        "-force_key_frames", f"expr:gte(t,n_forced*{chunk_duration_sec})",
        "-c:v", "libx264", "-preset", "ultrafast",
        "-an",
        "-reset_timestamps", "1",
        os.path.join(local_chunk_dir, "chunk_%03d.mp4")
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    local_chunks = sorted([
        os.path.join(local_chunk_dir, f)
        for f in os.listdir(local_chunk_dir)
        if f.startswith("chunk_")
    ])

    chunk_keys = []
    for index, local_path in enumerate(local_chunks):
        chunk_key = f"{video_id}_{index}.mp4"
        upload_file(local_path, chunk_key)
        chunk_keys.append(chunk_key)

    audio = f"{video_id}_audio.aac"
    upload_file(local_audio_path, audio)



    os.remove(local_input)
    os.remove(local_audio_path)
    for p in local_chunks:
        os.remove(p)
    os.rmdir(local_chunk_dir)

    return chunk_keys
