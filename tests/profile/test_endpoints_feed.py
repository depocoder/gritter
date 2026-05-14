from datetime import UTC, datetime, timedelta

from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from gritter.db.models.posts import Post, PostStatus
from tests.profile.helpers import auth_headers, register_and_login


def _published(user_id: int, *, offset_seconds: int = 0, title: str = "t") -> Post:
    base = datetime.now(tz=UTC).replace(tzinfo=None)
    return Post(
        user_id=user_id,
        title=title,
        content="c",
        status=PostStatus.published,
        created_at=base + timedelta(seconds=offset_seconds),
    )


async def test_feed_empty_when_no_follows(
    client: AsyncClient, fastapi_app: FastAPI
) -> None:
    _, tokens = await register_and_login(client, fastapi_app, "feed-empty")

    url = fastapi_app.url_path_for("get_my_feed")
    resp = await client.get(url, headers=auth_headers(tokens))

    assert resp.status_code == status.HTTP_200_OK
    body = resp.json()
    assert body == {
        "items": [],
        "total": 0,
        "page": 1,
        "size": 20,
        "has_next": False,
    }


async def test_feed_returns_only_published_from_followed(
    client: AsyncClient,
    fastapi_app: FastAPI,
    dbsession: AsyncSession,
) -> None:
    _, my_tokens = await register_and_login(client, fastapi_app, "feed-me")
    followed, _ = await register_and_login(client, fastapi_app, "feed-followed")
    other, _ = await register_and_login(client, fastapi_app, "feed-other")
    await client.post(
        fastapi_app.url_path_for("follow_user", user_id=followed["id"]),
        headers=auth_headers(my_tokens),
    )
    p_followed_pub = _published(followed["id"], title="seen")
    p_followed_mod = Post(user_id=followed["id"], title="hidden-mod", content="c")
    p_other_pub = _published(other["id"], title="hidden-other")
    dbsession.add_all([p_followed_pub, p_followed_mod, p_other_pub])
    await dbsession.flush()

    url = fastapi_app.url_path_for("get_my_feed")
    resp = await client.get(url, headers=auth_headers(my_tokens))

    body = resp.json()
    titles = [item["title"] for item in body["items"]]
    assert titles == ["seen"]
    assert body["total"] == 1


async def test_feed_pagination_has_next_flag(
    client: AsyncClient,
    fastapi_app: FastAPI,
    dbsession: AsyncSession,
) -> None:
    _, my_tokens = await register_and_login(client, fastapi_app, "feed-page-me")
    followed, _ = await register_and_login(client, fastapi_app, "feed-page-followed")
    await client.post(
        fastapi_app.url_path_for("follow_user", user_id=followed["id"]),
        headers=auth_headers(my_tokens),
    )
    for i in range(3):
        dbsession.add(_published(followed["id"], offset_seconds=i, title=f"p{i}"))
    await dbsession.flush()

    url = fastapi_app.url_path_for("get_my_feed")
    page1 = (
        await client.get(
            url, params={"page": 1, "size": 2}, headers=auth_headers(my_tokens)
        )
    ).json()
    page2 = (
        await client.get(
            url, params={"page": 2, "size": 2}, headers=auth_headers(my_tokens)
        )
    ).json()

    assert page1["total"] == 3
    assert page1["has_next"] is True
    assert len(page1["items"]) == 2
    assert page2["has_next"] is False
    assert len(page2["items"]) == 1


async def test_feed_validates_page(client: AsyncClient, fastapi_app: FastAPI) -> None:
    _, tokens = await register_and_login(client, fastapi_app, "feed-bad-page")

    url = fastapi_app.url_path_for("get_my_feed")
    resp = await client.get(url, params={"page": 0}, headers=auth_headers(tokens))

    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_feed_validates_size_lower_bound(
    client: AsyncClient, fastapi_app: FastAPI
) -> None:
    _, tokens = await register_and_login(client, fastapi_app, "feed-bad-size-lo")

    url = fastapi_app.url_path_for("get_my_feed")
    resp = await client.get(url, params={"size": 0}, headers=auth_headers(tokens))

    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_feed_validates_size_upper_bound(
    client: AsyncClient, fastapi_app: FastAPI
) -> None:
    _, tokens = await register_and_login(client, fastapi_app, "feed-bad-size-hi")

    url = fastapi_app.url_path_for("get_my_feed")
    resp = await client.get(url, params={"size": 101}, headers=auth_headers(tokens))

    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_feed_requires_auth(client: AsyncClient, fastapi_app: FastAPI) -> None:
    url = fastapi_app.url_path_for("get_my_feed")
    resp = await client.get(url)

    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
