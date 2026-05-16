"""Unit tests for :class:`gritter.db.dao.comments_dao.CommentDAO`."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gritter.db.dao.comments_dao import CommentDAO
from gritter.db.models.comments import Comment
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


async def test_create_persists_comment_and_increments_counter(
    dbsession: AsyncSession,
) -> None:
    user = await _make_user(dbsession, "dao-comm-1")
    post = await _make_post(dbsession, user.id)
    dao = CommentDAO(dbsession)

    comment = await dao.create(post_id=post.id, user_id=user.id, content="hello")

    assert comment.id > 0
    assert comment.created_at is not None
    refreshed = (
        await dbsession.execute(select(Post).where(Post.id == post.id))
    ).scalar_one()
    assert refreshed.comments_count == 1


async def test_soft_delete_marks_row_and_decrements_counter(
    dbsession: AsyncSession,
) -> None:
    user = await _make_user(dbsession, "dao-comm-2")
    post = await _make_post(dbsession, user.id)
    dao = CommentDAO(dbsession)
    comment = await dao.create(post_id=post.id, user_id=user.id, content="hello")

    await dao.soft_delete(comment)

    row = (
        await dbsession.execute(select(Comment).where(Comment.id == comment.id))
    ).scalar_one()
    assert row.deleted_at is not None
    refreshed = (
        await dbsession.execute(select(Post).where(Post.id == post.id))
    ).scalar_one()
    assert refreshed.comments_count == 0


async def test_get_by_id_hides_soft_deleted(dbsession: AsyncSession) -> None:
    user = await _make_user(dbsession, "dao-comm-3")
    post = await _make_post(dbsession, user.id)
    dao = CommentDAO(dbsession)
    comment = await dao.create(post_id=post.id, user_id=user.id, content="hello")
    await dao.soft_delete(comment)

    assert await dao.get_by_id(comment.id) is None


async def test_list_for_post_returns_oldest_first(
    dbsession: AsyncSession,
) -> None:
    user = await _make_user(dbsession, "dao-comm-4")
    post = await _make_post(dbsession, user.id)
    dao = CommentDAO(dbsession)
    for i in range(3):
        await dao.create(post_id=post.id, user_id=user.id, content=f"c-{i}")

    items = await dao.list_for_post(post.id, offset=0, limit=10)

    assert [c.content for c in items] == ["c-0", "c-1", "c-2"]


async def test_count_for_post_ignores_deleted(dbsession: AsyncSession) -> None:
    user = await _make_user(dbsession, "dao-comm-5")
    post = await _make_post(dbsession, user.id)
    dao = CommentDAO(dbsession)
    c1 = await dao.create(post_id=post.id, user_id=user.id, content="a")
    await dao.create(post_id=post.id, user_id=user.id, content="b")
    await dao.soft_delete(c1)

    assert await dao.count_for_post(post.id) == 1
