"""DAO for `posts_outbox` (write-side; the publisher polls this in Эпик 6)."""

from datetime import UTC, datetime
from typing import Any

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from gritter.db.dependencies import get_db_session
from gritter.db.models.posts_outbox import (
    POST_CREATED_EVENT,
    POST_UPDATED_EVENT,
    PostOutbox,
)


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
