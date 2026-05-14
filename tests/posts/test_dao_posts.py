from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from gritter.db.dao.posts_dao import PostDAO
from gritter.db.models.posts import Post, PostStatus
from gritter.db.models.users import User


def _user(login: str) -> User:
    return User(first_name="A", last_name="B", login=login, password_hash="x")


def _published(
    user_id: int,
    *,
    offset_seconds: int = 0,
    title: str = "t",
    category: str | None = None,
) -> Post:
    base = datetime.now(tz=UTC).replace(tzinfo=None)
    return Post(
        user_id=user_id,
        title=title,
        content="c",
        category=category,
        status=PostStatus.published,
        created_at=base + timedelta(seconds=offset_seconds),
    )


async def test_create_persists_on_moderation(dbsession: AsyncSession) -> None:
    dao = PostDAO(dbsession)
    author = _user("dao-create")
    dbsession.add(author)
    await dbsession.flush()

    post = await dao.create(user_id=author.id, title="t", content="c", category="news")

    assert post.id > 0
    assert post.status == PostStatus.on_moderation
    assert post.category == "news"


async def test_get_by_id_skips_soft_deleted(dbsession: AsyncSession) -> None:
    dao = PostDAO(dbsession)
    author = _user("dao-get-soft")
    dbsession.add(author)
    await dbsession.flush()
    post = await dao.create(user_id=author.id, title="t", content="c", category=None)
    await dao.soft_delete(post)

    fetched = await dao.get_by_id(post.id)

    assert fetched is None


async def test_reset_for_remoderation_on_content_change(
    dbsession: AsyncSession,
) -> None:
    dao = PostDAO(dbsession)
    author = _user("dao-reset")
    dbsession.add(author)
    await dbsession.flush()
    post = await dao.create(user_id=author.id, title="t", content="c", category=None)
    post.status = PostStatus.published
    await dbsession.flush()

    await dao.reset_for_remoderation(post, content="changed")

    assert post.content == "changed"
    assert post.status == PostStatus.on_moderation


async def test_reset_for_remoderation_only_category_keeps_published(
    dbsession: AsyncSession,
) -> None:
    dao = PostDAO(dbsession)
    author = _user("dao-cat-only")
    dbsession.add(author)
    await dbsession.flush()
    post = await dao.create(user_id=author.id, title="t", content="c", category=None)
    post.status = PostStatus.published
    await dbsession.flush()

    await dao.reset_for_remoderation(post, category="news")

    assert post.category == "news"
    assert post.status == PostStatus.published


async def test_count_published_with_filters(dbsession: AsyncSession) -> None:
    dao = PostDAO(dbsession)
    a, b = _user("dao-count-a"), _user("dao-count-b")
    dbsession.add_all([a, b])
    await dbsession.flush()
    dbsession.add_all(
        [
            _published(a.id, category="news"),
            _published(a.id, category="tech"),
            _published(b.id, category="news"),
        ]
    )
    await dbsession.flush()

    only_a_news = await dao.count_published(author_id=a.id, category="news")

    assert only_a_news == 1


async def test_list_published_orders_desc(dbsession: AsyncSession) -> None:
    dao = PostDAO(dbsession)
    author = _user("dao-list-order")
    dbsession.add(author)
    await dbsession.flush()
    older = _published(author.id, offset_seconds=0, title="old")
    newer = _published(author.id, offset_seconds=10, title="new")
    dbsession.add_all([older, newer])
    await dbsession.flush()

    posts = await dao.list_published(offset=0, limit=10)

    assert [p.title for p in posts] == ["new", "old"]


async def test_list_published_filters_date_range(
    dbsession: AsyncSession,
) -> None:
    dao = PostDAO(dbsession)
    author = _user("dao-list-dates")
    dbsession.add(author)
    await dbsession.flush()
    early = _published(author.id, offset_seconds=0, title="early")
    late = _published(author.id, offset_seconds=100, title="late")
    dbsession.add_all([early, late])
    await dbsession.flush()
    cutoff = early.created_at + timedelta(seconds=50)

    posts = await dao.list_published(offset=0, limit=10, date_from=cutoff)

    assert [p.title for p in posts] == ["late"]


async def test_count_by_author_excludes_soft_deleted(
    dbsession: AsyncSession,
) -> None:
    dao = PostDAO(dbsession)
    author = _user("dao-author-counts")
    dbsession.add(author)
    await dbsession.flush()
    p = await dao.create(user_id=author.id, title="t", content="c", category=None)
    await dao.soft_delete(p)

    assert await dao.count_by_author(author.id) == 0


async def test_list_by_author_filters_status(dbsession: AsyncSession) -> None:
    dao = PostDAO(dbsession)
    author = _user("dao-author-status")
    dbsession.add(author)
    await dbsession.flush()
    p_mod = await dao.create(user_id=author.id, title="m", content="c", category=None)
    p_pub = await dao.create(user_id=author.id, title="p", content="c", category=None)
    p_pub.status = PostStatus.published
    await dbsession.flush()

    only_pub = await dao.list_by_author(
        author.id, offset=0, limit=10, status=PostStatus.published
    )
    only_mod = await dao.list_by_author(
        author.id, offset=0, limit=10, status=PostStatus.on_moderation
    )

    assert [p.id for p in only_pub] == [p_pub.id]
    assert [p.id for p in only_mod] == [p_mod.id]


async def test_count_feed_zero_when_no_authors(dbsession: AsyncSession) -> None:
    dao = PostDAO(dbsession)
    assert await dao.count_feed([]) == 0


async def test_list_feed_empty_when_no_authors(dbsession: AsyncSession) -> None:
    dao = PostDAO(dbsession)
    assert list(await dao.list_feed([], offset=0, limit=10)) == []
