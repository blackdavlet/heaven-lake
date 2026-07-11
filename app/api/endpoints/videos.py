import uuid
import asyncio
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.repositories.video_repo import VideoRepository
from app.clients.minio_client import presigned_upload_url, upload_exists, presigned_download_url, delete_objects
from app.clients.redis_client import get_progress, is_transcoding_complete, set_chunk_total
from app.messaging.publisher import publish_chunk_job
from app.workers.splitter import split_video

router = APIRouter(prefix="/videos", tags=["videos"])

TARGET_RESOLUTIONS = ["480p", "720p", "1080p"]


def video_storage_keys(video_id: uuid.UUID, chunk_count: int | None) -> list[str]:
    video_id_str = str(video_id)
    keys = [f"{video_id_str}.mp4", f"{video_id_str}_audio.aac"]
    keys.extend(f"{video_id_str}_{resolution}.mp4" for resolution in TARGET_RESOLUTIONS)

    for chunk_index in range(chunk_count or 0):
        keys.append(f"{video_id_str}_{chunk_index}.mp4")
        keys.extend(
            f"{video_id_str}_{chunk_index}_{resolution}.mp4"
            for resolution in TARGET_RESOLUTIONS
        )

    return keys


@router.post("/upload")
async def request_upload(filename: str, session: AsyncSession = Depends(get_session)):
    repo = VideoRepository(session)
    video = await repo.create_video(filename=filename)

    url = await asyncio.to_thread(presigned_upload_url, video.object_key)

    return {
        "video_id": video.video_id,
        "upload_url": url,
        "object_key": video.object_key
    }


@router.post("/{video_id}/confirm")
async def confirm_upload(video_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    repo = VideoRepository(session)
    video = await repo.get_video(video_id)

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    exists = await asyncio.to_thread(upload_exists, video.object_key)
    if not exists:
        raise HTTPException(status_code=400, detail="Video not found in storage, upload first")

    await repo.update_status(video_id, "splitting")

    chunk_keys = await asyncio.to_thread(split_video, str(video_id))
    chunk_count = len(chunk_keys)

    await repo.set_chunk_count(video_id, chunk_count)
    await repo.update_status(video_id, "transcoding")

    for resolution in TARGET_RESOLUTIONS:
        await set_chunk_total(str(video_id), resolution, chunk_count)

    for chunk_index in range(chunk_count):
        for resolution in TARGET_RESOLUTIONS:
            await publish_chunk_job(str(video_id), chunk_index, resolution, chunk_count)

    return {
        "video_id": video_id,
        "status": "transcoding",
        "chunks": chunk_count,
        "resolutions": TARGET_RESOLUTIONS
    }

@router.get("/{video_id}/status")
async def get_status(video_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    repo = VideoRepository(session)
    video = await repo.get_video(video_id)

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    progress = {}
    for resolution in TARGET_RESOLUTIONS:
        completed, total = await get_progress(str(video_id), resolution)
        if total == 0:
            is_done = await asyncio.to_thread(upload_exists, f"{video_id}_{resolution}.mp4")
            progress[resolution] = {"completed": None, "total": None, "done": is_done}
        else:
            progress[resolution] = {
                "completed": completed,
                "total": total,
                "done": completed >= total
            }

    return {"video_id": video_id, "status": video.status, "progress": progress}

"""
@router.get("/{video_id}/status")
async def get_status(video_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    repo = VideoRepository(session)
    video = await repo.get_video(video_id)

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    progress = {}
    for resolution in TARGET_RESOLUTIONS:
        completed, total = await get_progress(str(video_id), resolution)
        progress[resolution] = {
            "completed": completed,
            "total": total,
            "done": completed >= total and total > 0
        }

    return {
        "video_id": video_id,
        "status": video.status,
        "progress": progress
    }
"""

@router.delete("/{video_id}")
async def delete_video(video_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    repo = VideoRepository(session)
    video = await repo.get_video(video_id)

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    object_keys = video_storage_keys(video_id, video.chunk_count)
    await asyncio.to_thread(delete_objects, object_keys)
    await repo.mark_deleted(video_id)
    await mark_video_deleted(str(video_id))
    return {
        "video_id": video_id,
        "status": "deleted",
        "deleted_objects": len(object_keys)
    }

@router.get("/{video_id}/download")
async def download_video(video_id: uuid.UUID, resolution: str, session: AsyncSession = Depends(get_session)):
    repo = VideoRepository(session)
    video = await repo.get_video(video_id)

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    object_key = f"{video_id}_{resolution}.mp4"
    exists = await asyncio.to_thread(upload_exists, object_key)

    if not exists:
        raise HTTPException(status_code=400, detail=f"{resolution} not ready yet")

    url = await asyncio.to_thread(presigned_download_url, object_key)
    return {"download_url": url}

"""
@router.get("/{video_id}/download")
async def download_video(video_id: uuid.UUID, resolution: str = "720p", session: AsyncSession = Depends(get_session)):
    repo = VideoRepository(session)
    video = await repo.get_video(video_id)

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    if not await is_transcoding_complete(str(video_id), resolution):
        raise HTTPException(status_code=400, detail=f"{resolution} not ready yet")

    object_key = f"{video_id}_{resolution}.mp4"
    url = await asyncio.to_thread(presigned_download_url, object_key)

    return {"download_url": url}
"""
