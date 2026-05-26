"""DAO for `posts_outbox` (write-side; the publisher polls this in Эпик 6)."""

from datetime import UTC, datetime
from typing import Any

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gritter.db.dependencies import get_db_session
from gritter.db.models.posts_outbox import (
    POST_CREATED_EVENT,
    POST_UPDATED_EVENT,
    OutboxStatus,
    PostOutbox,
)
from gritter.settings import settings

batch_size = settings.batch_size


class PostsOutboxDAO:
    """Append-only writes to `posts_outbox` (in the caller's transaction)."""

    def __init__(self, session: AsyncSession = Depends(get_db_session)) -> None:
        self.session = session

    async def enqueue_created(self, post_id: int) -> PostOutbox:
        """Enqueue a `post.created` event for `post_id`."""
        return await self._enqueue(post_id, POST_CREATED_EVENT)

    async def enqueue_updated(self, post_id: int) -> PostOutbox:
        """Enqueue a `post.updated` event for `post_id`."""
        return await self._enqueue(post_id, POST_UPDATED_EVENT)

    async def get_posts(self, batch_size: int = batch_size) -> list[PostOutbox]:
        """Returns posts for RabbitMQ."""
        posts = (
            select(PostOutbox)
            .where(PostOutbox.status == OutboxStatus.pending, PostOutbox.attempts < 5)
            .order_by(PostOutbox.created_at)
            .limit(batch_size)
            .with_for_update(of=PostOutbox, skip_locked=True)
        )
        result = await self.session.execute(posts)
        return list(result.scalars().all())

    async def mark_sent(self, raw: PostOutbox) -> None:
        """Post uccessfully sent."""
        raw.status = OutboxStatus.sent
        raw.sent_at = datetime.now(tz=UTC).replace(tzinfo=None)

    async def mark_failed(self, raw: PostOutbox, error: str) -> None:
        """Unsuccessful sent -> catch error."""
        raw.attempts += 1
        raw.last_error = error

    async def _enqueue(self, post_id: int, event_type: str) -> PostOutbox:
        payload: dict[str, Any] = {
            "post_id": post_id,
            "event_type": event_type,
            "occurred_at": datetime.now(tz=UTC).isoformat(),
        }
        row = PostOutbox(
            aggregate_id=post_id,
            event_type=event_type,
            payload=payload,
        )
        self.session.add(row)
        await self.session.flush()
        return row
