from fastapi import FastAPI
from app.api.endpoints.videos import router as videos_router
from app.clients.minio_client import get_s3_client, BUCKET
import asyncio

app = FastAPI(title="HeavenLake")
app.include_router(videos_router)

@app.on_event("startup")
async def startup():
    def create_bucket():
        s3 = get_s3_client()
        existing = [b["Name"] for b in s3.list_buckets()["Buckets"]]
        if BUCKET not in existing:
            s3.create_bucket(Bucket=BUCKET)
    await asyncio.to_thread(create_bucket)

@app.get("/health")
async def health():
    return {"status": "ok"}