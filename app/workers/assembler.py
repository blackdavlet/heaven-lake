import os
import subprocess
from app.clients.minio_client import upload_file, download_file

def assemble_video(video_id: str, chunk_count: int, resolution: str) -> str:
    local_chunk_paths = []
    local_chunk_dir = f"/tmp/{video_id}_{resolution}_assembly"
    os.makedirs(local_chunk_dir, exist_ok=True)

    for i in range(chunk_count):
        chunk_key = f"{video_id}_{i}_{resolution}.mp4"
        local_path = os.path.join(local_chunk_dir, f"chunk_{i}.mp4")
        download_file(chunk_key, local_path)
        local_chunk_paths.append(local_path)

    manifest_path = os.path.join(local_chunk_dir, "manifest.txt")
    with open(manifest_path, "w") as f:
        for path in local_chunk_paths:
            abs_path = os.path.abspath(path).replace("\\", "/")
            f.write(f"file '{abs_path}'\n")

    local_output = os.path.join(local_chunk_dir, "output.mp4")
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", manifest_path,
        "-c", "copy",
        local_output
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    output_key = f"{video_id}_{resolution}.mp4"
    upload_file(local_output, output_key)

    for p in local_chunk_paths:
        os.remove(p)
    os.remove(manifest_path)
    os.remove(local_output)
    os.rmdir(local_chunk_dir)

    return output_key