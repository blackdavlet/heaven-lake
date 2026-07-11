import os
import subprocess
from app.clients.minio_client import upload_file, download_file

RESOLUTIONS = {
    "480p": "854:480",
    "720p": "1280:720",
    "1080p": "1920:1080",
}

def transcode_chunk(video_id: str, chunk_index: int, resolution: str) -> str:
    scale = RESOLUTIONS[resolution]
    raw_key = f"{video_id}_{chunk_index}.mp4"
    output_key = f"{video_id}_{chunk_index}_{resolution}.mp4"

    local_input = f"/tmp/{video_id}_{chunk_index}_{resolution}_raw.mp4"
    local_output = f"/tmp/{video_id}_{chunk_index}_{resolution}.mp4"

    download_file(raw_key, local_input)

    cmd = [
        "ffmpeg", "-y",
        "-fflags", "+genpts",
        "-i", local_input,
        "-vf", f"scale={scale}",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "26",
        "-avoid_negative_ts", "make_zero",
        "-fps_mode", "cfr",
        local_output
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    upload_file(local_output, output_key)

    os.remove(local_input)
    os.remove(local_output)

    return output_key












"""
def transcode_chunk(video_id: str, chunk_index: int, resolution: str) -> str:
    scale = RESOLUTIONS[resolution]
    raw_key = f"{video_id}_{chunk_index}.mp4"
    output_key = f"{video_id}_{chunk_index}_{resolution}.mp4"

    local_input = f"/tmp/{video_id}_{chunk_index}_raw.mp4"
    local_output = f"/tmp/{video_id}_{chunk_index}_{resolution}.mp4"

    download_file(raw_key, local_input)

    cmd = [
        "ffmpeg", "-y",
        "-fflags", "+genpts",
        "-i", local_input,
        "-vf", f"scale={scale}",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "26",
        "-avoid_negative_ts", "make_zero",
        "-fps_mode", "cfr",
        local_output
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    upload_file(local_output, output_key)

    os.remove(local_input)
    os.remove(local_output)

    return output_key
"""
