import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from gritter.db.models.posts import (
    AgeRating,
    Post,
    PostStatus,
    Sentiment,
)
from gritter.db.models.posts_outbox import (
    POST_CREATED_EVENT,
    OutboxStatus,
    PostOutbox,
)
from gritter.db.models.users import User


def _user(login: str) -> User:
    return User(first_name="A", last_name="B", login=login, password_hash="x")


async def test_post_default_counters_are_zero(dbsession: AsyncSession) -> None:
    author = _user("p-counters")
    dbsession.add(author)
    await dbsession.flush()

    post = Post(user_id=author.id, title="t", content="c")
    dbsession.add(post)
    await dbsession.flush()
    await dbsession.refresh(post)

    assert post.likes_count == 0
    assert post.comments_count == 0
    assert post.moderation_attempts == 0
    assert post.sentiment is None
    assert post.age_rating is None


async def test_post_persists_classification(dbsession: AsyncSession) -> None:
    author = _user("p-classified")
    dbsession.add(author)
    await dbsession.flush()
    post = Post(user_id=author.id, title="t", content="c")
    dbsession.add(post)
    await dbsession.flush()

    post.sentiment = Sentiment.positive
    post.age_rating = AgeRating.AGE_12
    post.status = PostStatus.published
    await dbsession.flush()
    await dbsession.refresh(post)

    assert post.sentiment == Sentiment.positive
    assert post.age_rating == AgeRating.AGE_12


async def test_likes_count_check_constraint_blocks_negative(
    dbsession: AsyncSession,
) -> None:
    author = _user("p-check-likes")
    dbsession.add(author)
    await dbsession.flush()
    post = Post(user_id=author.id, title="t", content="c")
    dbsession.add(post)
    await dbsession.flush()

    async with dbsession.begin_nested() as savepoint:
        post.likes_count = -1
        with pytest.raises(IntegrityError):
            await dbsession.flush()
        await savepoint.rollback()


async def test_outbox_default_status_pending(dbsession: AsyncSession) -> None:
    row = PostOutbox(
        aggregate_id=1,
        event_type=POST_CREATED_EVENT,
        payload={"post_id": 1},
    )
    dbsession.add(row)
    await dbsession.flush()
    await dbsession.refresh(row)

    assert row.status == OutboxStatus.pending
    assert row.attempts == 0
