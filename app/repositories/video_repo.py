import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import Video


class VideoRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_video(self, filename: str) -> Video:
        video = Video(filename=filename)
        self.session.add(video)
        await self.session.commit()
        await self.session.refresh(video)
        return video

    async def get_video(self, video_id: uuid.UUID) -> Video | None:
        result = await self.session.execute(
            select(Video).where(Video.video_id == video_id)
        )
        return result.scalar_one_or_none()

    async def update_status(self, video_id: uuid.UUID, status: str) -> None:
        video = await self.get_video(video_id)
        if video:
            video.status = status
            await self.session.commit()

    async def set_chunk_count(self, video_id: uuid.UUID, count: int) -> None:
        video = await self.get_video(video_id)
        if video:
            video.chunk_count = count
            await self.session.commit()

    async def get_chunk_count(self, video_id: uuid.UUID) -> int:
        video = await self.get_video(video_id)
        if video and video.chunk_count:
            return video.chunk_count
        return 0