import json
import os
import aio_pika

RABBITMQ_URL = os.environ["RABBITMQ_URL"]

async def get_connection():
    return await aio_pika.connect_robust(RABBITMQ_URL)

async def publish_resolution_job(video_id: str, resolution: str, chunk_count: int):
    connection = await get_connection()
    async with connection:
        channel = await connection.channel()
        queue = await channel.declare_queue("transcode_jobs", durable=True)
        message = {
            "video_id": video_id,
            "resolution": resolution,
            "chunk_count": chunk_count,
        }
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(message).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=queue.name
        )