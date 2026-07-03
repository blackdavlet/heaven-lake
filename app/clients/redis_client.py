import os
import redis.asyncio as aioredis

REDIS_URL = os.environ["REDIS_URL"]

def get_redis():
    return aioredis.from_url(REDIS_URL, decode_responses=True)


async def set_chunk_total(video_id: str, resolution: str, total: int, ttl: int = 86400) -> None:
    async with get_redis() as redis:
        key = f"{video_id}:{resolution}:total"
        await redis.set(key, total, ex=ttl)


async def increment_completed(video_id: str, resolution: str) -> int:
    async with get_redis() as redis:
        key = f"{video_id}:{resolution}:completed"
        return await redis.incr(key)


async def get_progress(video_id: str, resolution: str) -> tuple[int, int]:
    async with get_redis() as redis:
        total = await redis.get(f"{video_id}:{resolution}:total")
        completed = await redis.get(f"{video_id}:{resolution}:completed")
        return int(completed or 0), int(total or 0)


async def is_transcoding_complete(video_id: str, resolution: str) -> bool:
    completed, total = await get_progress(video_id, resolution)
    if total == 0:
        return False
    return completed >= total


async def cleanup_progress(video_id: str, resolution: str) -> None:
    async with get_redis() as redis:
        await redis.delete(
            f"{video_id}:{resolution}:total",
            f"{video_id}:{resolution}:completed"
        )