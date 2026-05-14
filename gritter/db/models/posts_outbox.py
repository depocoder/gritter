"""Transactional-outbox row for `posts.created` / `posts.updated` events.

Эпик 2 only writes to this table from the API.  The polling publisher that
drains it into RabbitMQ lives in Эпик 6.
"""

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, Enum, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from gritter.db.base import Base


class OutboxStatus(enum.StrEnum):
    """Lifecycle of an outbox row."""

    pending = "pending"
    sent = "sent"


POST_CREATED_EVENT = "post.created"
POST_UPDATED_EVENT = "post.updated"


class PostOutbox(Base):
    """One pending/sent event for a post."""

    __tablename__ = "posts_outbox"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    aggregate_id: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[OutboxStatus] = mapped_column(
        Enum(OutboxStatus, name="outbox_status"),
        nullable=False,
        server_default=OutboxStatus.pending.value,
    )
    attempts: Mapped[int] = mapped_column(nullable=False, server_default="0")
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
