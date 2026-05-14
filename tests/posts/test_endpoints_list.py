from datetime import UTC, datetime, timedelta

from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from gritter.db.models.posts import Post, PostStatus
from tests.posts.helpers import register_and_login


def _published(
    user_id: int,
    *,
    title: str = "t",
    category: str | None = None,
    offset_seconds: int = 0,
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


async def test_list_posts_returns_only_published(
    client: AsyncClient,
    fastapi_app: FastAPI,
    dbsession: AsyncSession,
) -> None:
    author, _ = await register_and_login(client, fastapi_app, "list-only-pub")
    pub = _published(author["id"], title="pub")
    on_mod = Post(user_id=author["id"], title="mod", content="c")
    deleted = _published(author["id"], title="gone")
    deleted.deleted_at = datetime.now(tz=UTC).replace(tzinfo=None)
    dbsession.add_all([pub, on_mod, deleted])
    await dbsession.flush()

    url = fastapi_app.url_path_for("list_posts")
    resp = await client.get(url)

    body = resp.json()
    titles = [item["title"] for item in body["items"]]
    assert titles == ["pub"]
    assert body["total"] == 1


async def test_list_posts_anonymous_works(
    client: AsyncClient, fastapi_app: FastAPI
) -> None:
    url = fastapi_app.url_path_for("list_posts")
    resp = await client.get(url)

    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == {
        "items": [],
        "total": 0,
        "page": 1,
        "size": 20,
        "has_next": False,
    }


async def test_list_posts_filters_by_author_and_category(
    client: AsyncClient,
    fastapi_app: FastAPI,
    dbsession: AsyncSession,
) -> None:
    a, _ = await register_and_login(client, fastapi_app, "list-filt-a")
    b, _ = await register_and_login(client, fastapi_app, "list-filt-b")
    dbsession.add_all(
        [
            _published(a["id"], title="a-news", category="news"),
            _published(a["id"], title="a-tech", category="tech"),
            _published(b["id"], title="b-news", category="news"),
        ]
    )
    await dbsession.flush()

    url = fastapi_app.url_path_for("list_posts")
    resp = await client.get(url, params={"author_id": a["id"], "category": "news"})

    titles = [item["title"] for item in resp.json()["items"]]
    assert titles == ["a-news"]


async def test_list_posts_filters_by_date_range(
    client: AsyncClient,
    fastapi_app: FastAPI,
    dbsession: AsyncSession,
) -> None:
    author, _ = await register_and_login(client, fastapi_app, "list-dates")
    early = _published(author["id"], title="early", offset_seconds=0)
    late = _published(author["id"], title="late", offset_seconds=100)
    dbsession.add_all([early, late])
    await dbsession.flush()
    cutoff = (early.created_at + timedelta(seconds=50)).isoformat()

    url = fastapi_app.url_path_for("list_posts")
    resp = await client.get(url, params={"date_from": cutoff})

    titles = [item["title"] for item in resp.json()["items"]]
    assert titles == ["late"]


async def test_list_posts_pagination_has_next(
    client: AsyncClient,
    fastapi_app: FastAPI,
    dbsession: AsyncSession,
) -> None:
    author, _ = await register_and_login(client, fastapi_app, "list-page")
    for i in range(3):
        dbsession.add(_published(author["id"], title=f"p{i}", offset_seconds=i))
    await dbsession.flush()

    url = fastapi_app.url_path_for("list_posts")
    p1 = (await client.get(url, params={"page": 1, "size": 2})).json()
    p2 = (await client.get(url, params={"page": 2, "size": 2})).json()

    assert p1["has_next"] is True
    assert len(p1["items"]) == 2
    assert p2["has_next"] is False
    assert len(p2["items"]) == 1


async def test_list_posts_validates_size(
    client: AsyncClient, fastapi_app: FastAPI
) -> None:
    url = fastapi_app.url_path_for("list_posts")
    resp = await client.get(url, params={"size": 101})

    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_list_posts_includes_age_rating_field(
    client: AsyncClient,
    fastapi_app: FastAPI,
    dbsession: AsyncSession,
) -> None:
    author, _ = await register_and_login(client, fastapi_app, "list-age")
    p = _published(author["id"], title="a")
    dbsession.add(p)
    await dbsession.flush()

    url = fastapi_app.url_path_for("list_posts")
    resp = await client.get(url)

    item = resp.json()["items"][0]
    assert "age_rating" in item
    assert item["age_rating"] is None
    assert "author" in item
    assert item["author"]["login"] == "list-age"
