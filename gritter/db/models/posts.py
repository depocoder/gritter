"""Post entity (Эпик 2: full schema)."""

import enum
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from gritter.db.base import Base


class PostStatus(enum.StrEnum):
    """Lifecycle status for a post."""

    on_moderation = "on_moderation"
    published = "published"


class Sentiment(enum.StrEnum):
    """Tone classification produced by the moderation worker."""

    positive = "positive"
    neutral = "neutral"
    negative = "negative"


class AgeRating(enum.StrEnum):
    """Age-rating classification produced by the moderation worker."""

    AGE_0 = "0+"
    AGE_12 = "12+"
    AGE_16 = "16+"
    AGE_18 = "18+"


POST_TITLE_MAX_LEN = 120
POST_CONTENT_MAX_LEN = 280
POST_CATEGORY_MAX_LEN = 64


class Post(Base):
    """A user's mini-post."""

    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(POST_TITLE_MAX_LEN), nullable=False)
    content: Mapped[str] = mapped_column(String(POST_CONTENT_MAX_LEN), nullable=False)
    category: Mapped[str | None] = mapped_column(
        String(POST_CATEGORY_MAX_LEN), nullable=True
    )
    status: Mapped[PostStatus] = mapped_column(
        Enum(PostStatus, name="post_status"),
        nullable=False,
        server_default=PostStatus.on_moderation.value,
    )
    sentiment: Mapped[Sentiment | None] = mapped_column(
        Enum(Sentiment, name="sentiment"),
        nullable=True,
    )
    age_rating: Mapped[AgeRating | None] = mapped_column(
        Enum(
            AgeRating, name="age_rating", values_callable=lambda e: [m.value for m in e]
        ),
        nullable=True,
    )
    moderation_attempts: Mapped[int] = mapped_column(nullable=False, server_default="0")
    moderated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    likes_count: Mapped[int] = mapped_column(nullable=False, server_default="0")
    comments_count: Mapped[int] = mapped_column(nullable=False, server_default="0")

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_posts_user_created", "user_id", "created_at"),
        Index("idx_posts_status_created", "status", "created_at"),
        Index("idx_posts_category_created", "category", "created_at"),
        CheckConstraint("likes_count >= 0", name="chk_likes_count_nonneg"),
        CheckConstraint("comments_count >= 0", name="chk_comments_count_nonneg"),
    )
