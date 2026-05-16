"""Unit tests for :class:`gritter.db.dao.likes_dao.LikeDAO`."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gritter.db.dao.likes_dao import LikeDAO
from gritter.db.models.likes import Like
from gritter.db.models.posts import Post, PostStatus
from gritter.db.models.users import User


async def _make_user(dbsession: AsyncSession, login: str) -> User:
    user = User(
        first_name="Grace",
        last_name="Hopper",
        login=login,
        password_hash="x",
    )
    dbsession.add(user)
    await dbsession.flush()
    return user


async def _make_post(dbsession: AsyncSession, author_id: int) -> Post:
    post = Post(
        user_id=author_id,
        title="t",
        content="c",
        category=None,
        status=PostStatus.published,
    )
    dbsession.add(post)
    await dbsession.flush()
    return post


async def test_add_returns_true_then_false_for_duplicate(
    dbsession: AsyncSession,
) -> None:
    user = await _make_user(dbsession, "dao-like-1")
    post = await _make_post(dbsession, user.id)
    dao = LikeDAO(dbsession)

    first = await dao.add(post_id=post.id, user_id=user.id)
    second = await dao.add(post_id=post.id, user_id=user.id)

    assert first is True
    assert second is False
    rows = (await dbsession.execute(select(Like))).scalars().all()
    assert len(rows) == 1


async def test_add_increments_counter_only_on_first_insert(
    dbsession: AsyncSession,
) -> None:
    user = await _make_user(dbsession, "dao-like-2")
    post = await _make_post(dbsession, user.id)
    dao = LikeDAO(dbsession)

    await dao.add(post_id=post.id, user_id=user.id)
    await dao.add(post_id=post.id, user_id=user.id)

    refreshed = (
        await dbsession.execute(select(Post).where(Post.id == post.id))
    ).scalar_one()
    assert refreshed.likes_count == 1


async def test_remove_returns_true_then_false(dbsession: AsyncSession) -> None:
    user = await _make_user(dbsession, "dao-like-3")
    post = await _make_post(dbsession, user.id)
    dao = LikeDAO(dbsession)
    await dao.add(post_id=post.id, user_id=user.id)

    first = await dao.remove(post_id=post.id, user_id=user.id)
    second = await dao.remove(post_id=post.id, user_id=user.id)

    assert first is True
    assert second is False


async def test_remove_decrements_counter_only_when_row_existed(
    dbsession: AsyncSession,
) -> None:
    user = await _make_user(dbsession, "dao-like-4")
    post = await _make_post(dbsession, user.id)
    dao = LikeDAO(dbsession)
    await dao.add(post_id=post.id, user_id=user.id)

    await dao.remove(post_id=post.id, user_id=user.id)
    await dao.remove(post_id=post.id, user_id=user.id)  # second is no-op

    refreshed = (
        await dbsession.execute(select(Post).where(Post.id == post.id))
    ).scalar_one()
    assert refreshed.likes_count == 0
