# HeavenLake

A map reduce style video transcoding engine used to downscale the resolutions using FFMPEG

## Architecture

- **API** (FastAPI) — handles upload, confirm, status, download, delete
- **Worker** — consumes transcode jobs from RabbitMQ, runs ffmpeg, tracks 
  progress in Redis
- **Postgres** — video metadata (id, filename, status)
- **Redis** — ephemeral per-chunk progress counters
- **RabbitMQ** — job queue between API and workers
- **MinIO** — S3-compatible object storage for videos

## Flow

1. `POST /videos/upload` → get presigned upload URL
2. Client PUTs video directly to MinIO
3. `POST /videos/{id}/confirm` → splits video, publishes transcode jobs
4. Worker transcodes all chunks per resolution, assembles, cleans up
5. `GET /videos/{id}/status` → poll progress
6. `GET /videos/{id}/download?resolution=720p` → presigned download URL

## Running locally

docker compose up --build

## Testing

docker compose exec api pytest -v

## Roadmap
- Kubernetes deployment (see `/k8s` once added)
- Scene-aware chunk splitting