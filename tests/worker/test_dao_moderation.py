"""Tests for `PostDAO` moderation methods (Эпик 4: US-4.1)."""

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from gritter.db.dao.posts_dao import PostDAO
from gritter.db.models.posts import AgeRating, PostStatus, Sentiment
from gritter.db.models.users import User


def _user(login: str) -> User:
    return User(first_name="A", last_name="B", login=login, password_hash="x")


async def test_set_moderation_result_publishes_post(
    dbsession: AsyncSession,
) -> None:
    """`set_moderation_result` flips status to published and fills the verdict."""

    dao = PostDAO(dbsession)
    author = _user("dao-mod-publish")
    dbsession.add(author)
    await dbsession.flush()
    post = await dao.create(user_id=author.id, title="t", content="c", category=None)

    await dao.set_moderation_result(
        post,
        sentiment=Sentiment.positive,
        age_rating=AgeRating.AGE_0,
    )

    assert post.status == PostStatus.published
    assert post.sentiment == Sentiment.positive
    assert post.age_rating == AgeRating.AGE_0
    assert post.moderated_at is not None
    assert post.moderation_attempts == 1


async def test_set_moderation_result_uses_naive_datetime(
    dbsession: AsyncSession,
) -> None:
    """`moderated_at` must be tz-naive — asyncpg rejects aware datetimes."""

    dao = PostDAO(dbsession)
    author = _user("dao-mod-naive")
    dbsession.add(author)
    await dbsession.flush()
    post = await dao.create(user_id=author.id, title="t", content="c", category=None)

    await dao.set_moderation_result(
        post,
        sentiment=Sentiment.neutral,
        age_rating=AgeRating.AGE_12,
    )

    assert isinstance(post.moderated_at, datetime)
    assert post.moderated_at.tzinfo is None


async def test_bump_moderation_attempt_increments_counter(
    dbsession: AsyncSession,
) -> None:
    """`bump_moderation_attempt` only touches the counter."""

    dao = PostDAO(dbsession)
    author = _user("dao-mod-bump")
    dbsession.add(author)
    await dbsession.flush()
    post = await dao.create(user_id=author.id, title="t", content="c", category=None)

    await dao.bump_moderation_attempt(post)
    await dao.bump_moderation_attempt(post)

    assert post.moderation_attempts == 2
    assert post.status == PostStatus.on_moderation
    assert post.sentiment is None
    assert post.age_rating is None
    assert post.moderated_at is None
