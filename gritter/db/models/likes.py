"""Like entity (Эпик 3): idempotent toggle on a post by a user."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, PrimaryKeyConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from gritter.db.base import Base


class Like(Base):
    """A like placed on a post by a user.

    Uniqueness is enforced by the composite primary key ``(post_id, user_id)``;
    that same constraint is what ``INSERT ... ON CONFLICT DO NOTHING`` relies on
    to make the toggle endpoint idempotent.
    """

    __tablename__ = "likes"

    post_id: Mapped[int] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    __table_args__ = (
        PrimaryKeyConstraint("post_id", "user_id", name="pk_likes"),
        Index("idx_likes_user", "user_id"),
    )
