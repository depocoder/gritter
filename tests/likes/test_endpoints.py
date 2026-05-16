"""HTTP-level tests for like / unlike (US-3.1)."""

from datetime import datetime

from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from gritter.db.models.likes import Like
from gritter.db.models.posts import Post
from tests.likes.helpers import (
    auth_headers,
    create_post_via_api,
    publish_post,
    register_and_login,
)


async def _like_url(app: FastAPI, post_id: int) -> str:
    return app.url_path_for("like_post", post_id=post_id)


async def _unlike_url(app: FastAPI, post_id: int) -> str:
    return app.url_path_for("unlike_post", post_id=post_id)


async def _read_post(dbsession: AsyncSession, post_id: int) -> Post:
    return (
        await dbsession.execute(select(Post).where(Post.id == post_id))
    ).scalar_one()


async def test_post_like_inserts_row_and_increments_counter(
    client: AsyncClient, fastapi_app: FastAPI, dbsession: AsyncSession
) -> None:
    _, tokens = await register_and_login(client, fastapi_app, "liker-1")
    post_id = await create_post_via_api(client, fastapi_app, tokens)
    await publish_post(dbsession, post_id)

    resp = await client.post(
        await _like_url(fastapi_app, post_id), headers=auth_headers(tokens)
    )

    assert resp.status_code == status.HTTP_200_OK
    body = resp.json()
    assert body == {"liked": True, "likes_count": 1}

    post = await _read_post(dbsession, post_id)
    assert post.likes_count == 1
    rows = (await dbsession.execute(select(Like))).scalars().all()
    assert len(rows) == 1


async def test_post_like_is_idempotent(
    client: AsyncClient, fastapi_app: FastAPI, dbsession: AsyncSession
) -> None:
    _, tokens = await register_and_login(client, fastapi_app, "liker-2")
    post_id = await create_post_via_api(client, fastapi_app, tokens)
    await publish_post(dbsession, post_id)

    headers = auth_headers(tokens)
    url = await _like_url(fastapi_app, post_id)
    first = await client.post(url, headers=headers)
    second = await client.post(url, headers=headers)

    assert first.status_code == status.HTTP_200_OK
    assert second.status_code == status.HTTP_200_OK
    assert second.json() == {"liked": True, "likes_count": 1}

    post = await _read_post(dbsession, post_id)
    assert post.likes_count == 1


async def test_delete_like_decrements_counter(
    client: AsyncClient, fastapi_app: FastAPI, dbsession: AsyncSession
) -> None:
    _, tokens = await register_and_login(client, fastapi_app, "liker-3")
    post_id = await create_post_via_api(client, fastapi_app, tokens)
    await publish_post(dbsession, post_id)
    headers = auth_headers(tokens)

    await client.post(await _like_url(fastapi_app, post_id), headers=headers)
    resp = await client.delete(await _unlike_url(fastapi_app, post_id), headers=headers)

    assert resp.status_code == status.HTTP_204_NO_CONTENT
    post = await _read_post(dbsession, post_id)
    assert post.likes_count == 0
    rows = (await dbsession.execute(select(Like))).scalars().all()
    assert rows == []


async def test_delete_like_idempotent_when_absent(
    client: AsyncClient, fastapi_app: FastAPI, dbsession: AsyncSession
) -> None:
    _, tokens = await register_and_login(client, fastapi_app, "liker-4")
    post_id = await create_post_via_api(client, fastapi_app, tokens)
    await publish_post(dbsession, post_id)

    resp = await client.delete(
        await _unlike_url(fastapi_app, post_id), headers=auth_headers(tokens)
    )

    assert resp.status_code == status.HTTP_204_NO_CONTENT
    post = await _read_post(dbsession, post_id)
    assert post.likes_count == 0


async def test_like_requires_auth(
    client: AsyncClient, fastapi_app: FastAPI, dbsession: AsyncSession
) -> None:
    _, tokens = await register_and_login(client, fastapi_app, "liker-5")
    post_id = await create_post_via_api(client, fastapi_app, tokens)
    await publish_post(dbsession, post_id)

    resp = await client.post(await _like_url(fastapi_app, post_id))

    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


async def test_like_missing_post_404(client: AsyncClient, fastapi_app: FastAPI) -> None:
    _, tokens = await register_and_login(client, fastapi_app, "liker-6")

    resp = await client.post(
        await _like_url(fastapi_app, 999_999), headers=auth_headers(tokens)
    )

    assert resp.status_code == status.HTTP_404_NOT_FOUND


async def test_like_soft_deleted_post_404(
    client: AsyncClient, fastapi_app: FastAPI, dbsession: AsyncSession
) -> None:
    _, tokens = await register_and_login(client, fastapi_app, "liker-7")
    post_id = await create_post_via_api(client, fastapi_app, tokens)
    # Soft-delete the post directly via the DB (cheaper than calling the API).
    post = await _read_post(dbsession, post_id)
    post.deleted_at = datetime.now(tz=None)
    await dbsession.flush()

    resp = await client.post(
        await _like_url(fastapi_app, post_id), headers=auth_headers(tokens)
    )

    assert resp.status_code == status.HTTP_404_NOT_FOUND


async def test_like_others_on_moderation_post_404(
    client: AsyncClient, fastapi_app: FastAPI
) -> None:
    """A second user cannot see (or like) a post still on moderation."""
    _, author_tokens = await register_and_login(client, fastapi_app, "author-8")
    post_id = await create_post_via_api(client, fastapi_app, author_tokens)
    _, viewer_tokens = await register_and_login(client, fastapi_app, "viewer-8")

    resp = await client.post(
        await _like_url(fastapi_app, post_id),
        headers=auth_headers(viewer_tokens),
    )

    assert resp.status_code == status.HTTP_404_NOT_FOUND


async def test_author_can_like_own_on_moderation_post(
    client: AsyncClient, fastapi_app: FastAPI, dbsession: AsyncSession
) -> None:
    """The post owner is allowed to see and therefore like their draft."""
    _, tokens = await register_and_login(client, fastapi_app, "author-9")
    post_id = await create_post_via_api(client, fastapi_app, tokens)

    resp = await client.post(
        await _like_url(fastapi_app, post_id), headers=auth_headers(tokens)
    )

    assert resp.status_code == status.HTTP_200_OK
    post = await _read_post(dbsession, post_id)
    assert post.likes_count == 1
