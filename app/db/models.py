import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, Text, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Video(Base):
    __tablename__ = "videos"

    video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
        default=uuid.uuid4
    )
    filename:    Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status:      Mapped[str] = mapped_column(Text, nullable=False, server_default="pending")
    chunk_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at:  Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())
    updated_at:  Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())

    @property
    def object_key(self) -> str:
        return f"{self.video_id}.mp4"

    def assembled_key(self, resolution: str) -> str:
        return f"{self.video_id}_{resolution}.mp4"