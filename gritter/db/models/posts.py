"""Post entity (Эпик 5 stub: only what the feed needs).

Эпик 2 will extend this with sentiment, age_rating, moderation_attempts,
likes_count, comments_count, etc. For now we keep just enough to support
US-5.2 feed (and US-2.2 `status='published'` filter).
"""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from gritter.db.base import Base


class PostStatus(enum.StrEnum):
    """Lifecycle status for a post."""

    on_moderation = "on_moderation"
    published = "published"


class Post(Base):
    """A user's mini-post."""

    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    content: Mapped[str] = mapped_column(String(280), nullable=False)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[PostStatus] = mapped_column(
        Enum(PostStatus, name="post_status"),
        nullable=False,
        server_default=PostStatus.on_moderation.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
