"""Comment entity (Эпик 3): user comment on a post with soft-delete."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from gritter.db.base import Base

COMMENT_CONTENT_MAX_LEN = 500


class Comment(Base):
    """A comment on a post.

    Soft-deleted via ``deleted_at`` (mirrors the ``posts`` pattern) so the
    denormalised ``posts.comments_count`` can be decremented exactly once per
    delete while preserving an audit trail.
    """

    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    content: Mapped[str] = mapped_column(
        String(COMMENT_CONTENT_MAX_LEN), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (Index("idx_comments_post_created", "post_id", "created_at"),)
