import json
import asyncio
import os
import aio_pika

from app.db.session import AsyncSessionLocal
from app.repositories.video_repo import VideoRepository
from app.clients.redis_client import increment_completed, get_progress, cleanup_progress, is_video_deleted
from app.workers.downscaler import transcode_chunk
from app.workers.assembler import assemble_video
from app.clients.minio_client import delete_object, upload_exists

RABBITMQ_URL = os.environ["RABBITMQ_URL"]
MAX_CONCURRENT = int(os.getenv("MAX_CONCURRENT", str(os.cpu_count() or 4)))
TARGET_RESOLUTIONS = ["480p", "720p", "1080p"]

semaphore = asyncio.Semaphore(MAX_CONCURRENT)


async def get_video_or_none(video_id: str):
    async with AsyncSessionLocal() as session:
        repo = VideoRepository(session)
        return await repo.get_video(video_id)


async def finalize_resolution(video_id: str, resolution: str, chunk_count: int):
    print(f"[Worker] All chunks done for {video_id} @ {resolution}, assembling")
    await asyncio.to_thread(assemble_video, video_id, chunk_count, resolution)

    for i in range(chunk_count):
        await asyncio.to_thread(delete_object, f"{video_id}_{i}_{resolution}.mp4")

    await cleanup_progress(video_id, resolution)
    print(f"[Worker] {video_id} @ {resolution} assembled and cleaned up")

    all_done = True
    for res in TARGET_RESOLUTIONS:
        if res == resolution:
            continue
        exists = await asyncio.to_thread(upload_exists, f"{video_id}_{res}.mp4")
        if not exists:
            all_done = False
            break

    if all_done:
        for i in range(chunk_count):
            await asyncio.to_thread(delete_object, f"{video_id}_{i}.mp4")
            print(f"[Worker] Deleted raw chunk {i}")

        async with AsyncSessionLocal() as session:
            repo = VideoRepository(session)
            await repo.update_status(video_id, "ready")

        print(f"[Worker] {video_id} fully ready at all resolutions")

"""
async def handle_message(message: aio_pika.IncomingMessage):
    async with message.process():
        data = json.loads(message.body)
        video_id = data["video_id"]
        chunk_index = data["chunk_index"]
        resolution = data["resolution"]
        chunk_count = data["chunk_count"]

        video = await get_video_or_none(video_id)
        if not video or video.status == "deleted":
            print(f"[Worker] Skipping {video_id} chunk {chunk_index} deleted or missing")
            return

        async with semaphore:
            try:
                await asyncio.to_thread(transcode_chunk, video_id, chunk_index, resolution)
                completed = await increment_completed(video_id, resolution)
                print(f"[Worker] {video_id} @ {resolution} chunk {chunk_index} done ({completed}/{chunk_count})")

                if completed == chunk_count:
                    await finalize_resolution(video_id, resolution, chunk_count)

            except Exception as e:
                print(f"[Worker] ERROR processing {video_id} chunk {chunk_index} @ {resolution}: {e}")
                async with AsyncSessionLocal() as session:
                    repo = VideoRepository(session)
                    await repo.update_status(video_id, "failed")
                raise

"""
#redis checkout instead of postgre

async def handle_message(message: aio_pika.IncomingMessage):
    async with message.process():
        data = json.loads(message.body)
        video_id = data["video_id"]
        chunk_index = data["chunk_index"]
        resolution = data["resolution"]
        chunk_count = data["chunk_count"]

        if await is_video_deleted(video_id):
            print(f"[Worker] Skipping {video_id} chunk {chunk_index} — deleted")
            return

        async with semaphore:
            try:
                await asyncio.to_thread(transcode_chunk, video_id, chunk_index, resolution)
                completed = await increment_completed(video_id, resolution)
                print(f"[Worker] {video_id} @ {resolution} chunk {chunk_index} done ({completed}/{chunk_count})")

                if completed == chunk_count:
                    await finalize_resolution(video_id, resolution, chunk_count)

            except Exception as e:
                print(f"[Worker] ERROR processing {video_id} chunk {chunk_index} @ {resolution}: {e}")
                async with AsyncSessionLocal() as session:
                    repo = VideoRepository(session)
                    await repo.update_status(video_id, "failed")
                raise


async def main():
    print("[Worker] Starting, connecting to RabbitMQ...")
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=MAX_CONCURRENT)
        queue = await channel.declare_queue("transcode_jobs", durable=True)
        await queue.consume(handle_message)
        print(f"[Worker] Listening (max_concurrent={MAX_CONCURRENT})")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())

















#old per resolution code
"""
import json
import asyncio
import os
import aio_pika

from app.db.session import AsyncSessionLocal
from app.repositories.video_repo import VideoRepository
from app.clients.redis_client import increment_completed, is_transcoding_complete, cleanup_progress, set_chunk_total
from app.workers.downscaler import transcode_chunk
from app.workers.assembler import assemble_video
from app.clients.minio_client import delete_object, upload_file, download_file, upload_exists

RABBITMQ_URL = os.environ["RABBITMQ_URL"]
MAX_CONCURRENT = int(os.getenv("MAX_CONCURRENT", str(os.cpu_count() or 4)))
TARGET_RESOLUTIONS = ["480p", "720p", "1080p"]

semaphore = asyncio.Semaphore(MAX_CONCURRENT)


async def handle_message(message: aio_pika.IncomingMessage):
    async with message.process():
        data = json.loads(message.body)
        video_id = data["video_id"]
        resolution = data["resolution"]
        chunk_count = data["chunk_count"]

        async with AsyncSessionLocal() as session:
            repo = VideoRepository(session)
            video = await repo.get_video(video_id)
            if not video or video.status == "deleted":
                print(f"[Worker] Skipping {video_id} — deleted or missing")
                return
        
        print(f"[Worker] Starting {video_id} @ {resolution} ({chunk_count} chunks)")

        try:
            await set_chunk_total(video_id, resolution, chunk_count)

            async def process_chunk(chunk_index: int):
                async with semaphore:
                    await asyncio.to_thread(
                        transcode_chunk,
                        video_id,
                        chunk_index,
                        resolution
                    )
                    completed = await increment_completed(video_id, resolution)
                    print(f"[Worker] {video_id} @ {resolution} chunk {chunk_index} done ({completed}/{chunk_count})")

            await asyncio.gather(*[process_chunk(i) for i in range(chunk_count)])

            print(f"[Worker] Assembling {video_id} @ {resolution}")
            await asyncio.to_thread(assemble_video, video_id, chunk_count, resolution)

            for i in range(chunk_count):
                await asyncio.to_thread(delete_object, f"{video_id}_{i}_{resolution}.mp4")

            print(f"[Worker] {video_id} @ {resolution} assembled")

            all_done = True
            for res in TARGET_RESOLUTIONS:
                if res == resolution:
                    continue
                assembled_exists = await asyncio.to_thread(upload_exists, f"{video_id}_{res}.mp4")
                if not assembled_exists:
                    all_done = False
                    break

            if all_done:
                for i in range(chunk_count):
                    await asyncio.to_thread(delete_object, f"{video_id}_{i}.mp4")
                    print(f"[Worker] Deleted raw chunk {i}")

                async with AsyncSessionLocal() as session:
                    repo = VideoRepository(session)
                    await repo.update_status(video_id, "ready")

                print(f"[Worker] {video_id} fully ready at all resolutions")

        except Exception as e:
            print(f"[Worker] ERROR processing {video_id} @ {resolution}: {e}")
            async with AsyncSessionLocal() as session:
                repo = VideoRepository(session)
                await repo.update_status(video_id, "failed")
            raise


async def main():
    print("[Worker] Starting, connecting to RabbitMQ...")
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=len(TARGET_RESOLUTIONS))
        queue = await channel.declare_queue("transcode_jobs", durable=True)
        await queue.consume(handle_message)
        print(f"[Worker] Listening (max_concurrent={MAX_CONCURRENT})")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
"""
