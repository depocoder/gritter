from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gritter.db.models.follows import Follow
from gritter.db.models.posts import Post, PostStatus
from gritter.db.models.users import User


def _user(login: str) -> User:
    return User(
        first_name="A",
        last_name="B",
        login=login,
        password_hash="x",
    )


async def test_follow_round_trip(dbsession: AsyncSession) -> None:
    a, b = _user("a-rt"), _user("b-rt")
    dbsession.add_all([a, b])
    await dbsession.flush()

    dbsession.add(Follow(follower_id=a.id, followee_id=b.id))
    await dbsession.flush()

    edges = (await dbsession.execute(select(Follow))).scalars().all()
    assert (edges[0].follower_id, edges[0].followee_id) == (a.id, b.id)


async def test_post_default_status_is_on_moderation(
    dbsession: AsyncSession,
) -> None:
    author = _user("post-default")
    dbsession.add(author)
    await dbsession.flush()

    post = Post(user_id=author.id, title="t", content="c")
    dbsession.add(post)
    await dbsession.flush()
    await dbsession.refresh(post)

    assert post.status == PostStatus.on_moderation


async def test_post_can_be_published(dbsession: AsyncSession) -> None:
    author = _user("post-published")
    dbsession.add(author)
    await dbsession.flush()

    post = Post(
        user_id=author.id,
        title="t",
        content="c",
        status=PostStatus.published,
        created_at=datetime.now(tz=UTC).replace(tzinfo=None),
    )
    dbsession.add(post)
    await dbsession.flush()

    assert post.status == PostStatus.published
