from datetime import UTC, datetime

from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from gritter.db.models.posts import Post, PostStatus
from tests.posts.helpers import auth_headers, register_and_login


async def test_get_published_post_visible_to_anonymous(
    client: AsyncClient,
    fastapi_app: FastAPI,
    dbsession: AsyncSession,
) -> None:
    author, _ = await register_and_login(client, fastapi_app, "get-pub")
    p = Post(
        user_id=author["id"],
        title="t",
        content="c",
        status=PostStatus.published,
    )
    dbsession.add(p)
    await dbsession.flush()

    url = fastapi_app.url_path_for("get_post", post_id=p.id)
    resp = await client.get(url)

    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["id"] == p.id


async def test_get_on_moderation_post_404_for_anonymous(
    client: AsyncClient,
    fastapi_app: FastAPI,
    dbsession: AsyncSession,
) -> None:
    author, _ = await register_and_login(client, fastapi_app, "get-mod-anon")
    p = Post(user_id=author["id"], title="t", content="c")
    dbsession.add(p)
    await dbsession.flush()

    url = fastapi_app.url_path_for("get_post", post_id=p.id)
    resp = await client.get(url)

    assert resp.status_code == status.HTTP_404_NOT_FOUND


async def test_get_on_moderation_post_visible_to_author(
    client: AsyncClient,
    fastapi_app: FastAPI,
    dbsession: AsyncSession,
) -> None:
    author, tokens = await register_and_login(client, fastapi_app, "get-mod-auth")
    p = Post(user_id=author["id"], title="t", content="c")
    dbsession.add(p)
    await dbsession.flush()

    url = fastapi_app.url_path_for("get_post", post_id=p.id)
    resp = await client.get(url, headers=auth_headers(tokens))

    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["status"] == PostStatus.on_moderation.value


async def test_get_on_moderation_post_404_for_other_user(
    client: AsyncClient,
    fastapi_app: FastAPI,
    dbsession: AsyncSession,
) -> None:
    author, _ = await register_and_login(client, fastapi_app, "get-mod-author")
    _, viewer_tokens = await register_and_login(client, fastapi_app, "get-mod-viewer")
    p = Post(user_id=author["id"], title="t", content="c")
    dbsession.add(p)
    await dbsession.flush()

    url = fastapi_app.url_path_for("get_post", post_id=p.id)
    resp = await client.get(url, headers=auth_headers(viewer_tokens))

    assert resp.status_code == status.HTTP_404_NOT_FOUND


async def test_get_soft_deleted_post_404_even_for_author(
    client: AsyncClient,
    fastapi_app: FastAPI,
    dbsession: AsyncSession,
) -> None:
    author, tokens = await register_and_login(client, fastapi_app, "get-deleted")
    p = Post(
        user_id=author["id"],
        title="t",
        content="c",
        status=PostStatus.published,
        deleted_at=datetime.now(tz=UTC).replace(tzinfo=None),
    )
    dbsession.add(p)
    await dbsession.flush()

    url = fastapi_app.url_path_for("get_post", post_id=p.id)
    resp = await client.get(url, headers=auth_headers(tokens))

    assert resp.status_code == status.HTTP_404_NOT_FOUND


async def test_get_unknown_post_404(client: AsyncClient, fastapi_app: FastAPI) -> None:
    url = fastapi_app.url_path_for("get_post", post_id=10**9)
    resp = await client.get(url)

    assert resp.status_code == status.HTTP_404_NOT_FOUND


async def test_get_post_with_invalid_token_treated_as_anonymous(
    client: AsyncClient,
    fastapi_app: FastAPI,
    dbsession: AsyncSession,
) -> None:
    author, _ = await register_and_login(client, fastapi_app, "get-bad-tok")
    p = Post(
        user_id=author["id"],
        title="t",
        content="c",
        status=PostStatus.published,
    )
    dbsession.add(p)
    await dbsession.flush()

    url = fastapi_app.url_path_for("get_post", post_id=p.id)
    resp = await client.get(url, headers={"Authorization": "Bearer not.a.jwt"})

    assert resp.status_code == status.HTTP_200_OK
