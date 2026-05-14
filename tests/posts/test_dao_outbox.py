from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gritter.db.dao.posts_outbox_dao import PostsOutboxDAO
from gritter.db.models.posts_outbox import (
    POST_CREATED_EVENT,
    POST_UPDATED_EVENT,
    OutboxStatus,
    PostOutbox,
)


async def test_enqueue_created_writes_pending_row(
    dbsession: AsyncSession,
) -> None:
    dao = PostsOutboxDAO(dbsession)

    row = await dao.enqueue_created(post_id=42)

    persisted = (
        await dbsession.execute(select(PostOutbox).where(PostOutbox.id == row.id))
    ).scalar_one()
    assert persisted.aggregate_id == 42
    assert persisted.event_type == POST_CREATED_EVENT
    assert persisted.status == OutboxStatus.pending
    assert persisted.payload["post_id"] == 42
    assert persisted.payload["event_type"] == POST_CREATED_EVENT
    assert "occurred_at" in persisted.payload


async def test_enqueue_updated_uses_post_updated_event(
    dbsession: AsyncSession,
) -> None:
    dao = PostsOutboxDAO(dbsession)

    row = await dao.enqueue_updated(post_id=7)

    assert row.event_type == POST_UPDATED_EVENT
    assert row.payload["event_type"] == POST_UPDATED_EVENT
