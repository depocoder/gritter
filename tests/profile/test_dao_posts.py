from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from gritter.db.dao.posts_dao import PostDAO
from gritter.db.models.posts import Post, PostStatus
from gritter.db.models.users import User


def _user(login: str) -> User:
    return User(first_name="A", last_name="B", login=login, password_hash="x")


def _published(user_id: int, *, offset_seconds: int = 0) -> Post:
    base = datetime.now(tz=UTC).replace(tzinfo=None)
    return Post(
        user_id=user_id,
        title="t",
        content="c",
        status=PostStatus.published,
        created_at=base + timedelta(seconds=offset_seconds),
    )


async def test_count_feed_zero_when_no_authors(dbsession: AsyncSession) -> None:
    dao = PostDAO(dbsession)

    total = await dao.count_feed([])

    assert total == 0


async def test_list_feed_empty_when_no_authors(dbsession: AsyncSession) -> None:
    dao = PostDAO(dbsession)

    posts = await dao.list_feed([], offset=0, limit=10)

    assert list(posts) == []


async def test_count_feed_filters_status_and_deleted(dbsession: AsyncSession) -> None:
    dao = PostDAO(dbsession)
    author = _user("p-filt")
    dbsession.add(author)
    await dbsession.flush()
    pub = _published(author.id)
    on_mod = Post(user_id=author.id, title="t", content="c")
    deleted = _published(author.id)
    deleted.deleted_at = datetime.now(tz=UTC).replace(tzinfo=None)
    dbsession.add_all([pub, on_mod, deleted])
    await dbsession.flush()

    total = await dao.count_feed([author.id])

    assert total == 1


async def test_list_feed_orders_desc_and_paginates(dbsession: AsyncSession) -> None:
    dao = PostDAO(dbsession)
    author = _user("p-page")
    dbsession.add(author)
    await dbsession.flush()
    older = _published(author.id, offset_seconds=0)
    newer = _published(author.id, offset_seconds=10)
    dbsession.add_all([older, newer])
    await dbsession.flush()

    page1 = await dao.list_feed([author.id], offset=0, limit=1)
    page2 = await dao.list_feed([author.id], offset=1, limit=1)

    assert [p.id for p in page1] == [newer.id]
    assert [p.id for p in page2] == [older.id]
