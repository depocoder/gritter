"""HTTP-level tests for ``POST /api/posts/{id}/comments`` (US-3.2)."""

from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from gritter.db.models.comments import Comment
from gritter.db.models.posts import Post
from tests.comments.helpers import (
    auth_headers,
    create_post_via_api,
    publish_post,
    register_and_login,
)


async def _post_comments_url(app: FastAPI, post_id: int) -> str:
    return app.url_path_for("create_comment", post_id=post_id)


async def test_create_comment_persists_and_increments_counter(
    client: AsyncClient, fastapi_app: FastAPI, dbsession: AsyncSession
) -> None:
    user_json, tokens = await register_and_login(client, fastapi_app, "commenter-1")
    post_id = await create_post_via_api(client, fastapi_app, tokens)
    await publish_post(dbsession, post_id)

    resp = await client.post(
        await _post_comments_url(fastapi_app, post_id),
        json={"content": "first!"},
        headers=auth_headers(tokens),
    )

    assert resp.status_code == status.HTTP_201_CREATED
    body = resp.json()
    assert body["id"] > 0
    assert body["post_id"] == post_id
    assert body["content"] == "first!"
    assert body["author"]["login"] == user_json["login"]

    rows = (await dbsession.execute(select(Comment))).scalars().all()
    assert len(rows) == 1
    post = (
        await dbsession.execute(select(Post).where(Post.id == post_id))
    ).scalar_one()
    assert post.comments_count == 1


async def test_create_comment_requires_auth(
    client: AsyncClient, fastapi_app: FastAPI, dbsession: AsyncSession
) -> None:
    _, tokens = await register_and_login(client, fastapi_app, "commenter-2")
    post_id = await create_post_via_api(client, fastapi_app, tokens)
    await publish_post(dbsession, post_id)

    resp = await client.post(
        await _post_comments_url(fastapi_app, post_id),
        json={"content": "anon"},
    )

    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


async def test_create_comment_rejects_empty_content(
    client: AsyncClient, fastapi_app: FastAPI, dbsession: AsyncSession
) -> None:
    _, tokens = await register_and_login(client, fastapi_app, "commenter-3")
    post_id = await create_post_via_api(client, fastapi_app, tokens)
    await publish_post(dbsession, post_id)

    resp = await client.post(
        await _post_comments_url(fastapi_app, post_id),
        json={"content": ""},
        headers=auth_headers(tokens),
    )

    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_create_comment_rejects_overlong_content(
    client: AsyncClient, fastapi_app: FastAPI, dbsession: AsyncSession
) -> None:
    _, tokens = await register_and_login(client, fastapi_app, "commenter-4")
    post_id = await create_post_via_api(client, fastapi_app, tokens)
    await publish_post(dbsession, post_id)

    resp = await client.post(
        await _post_comments_url(fastapi_app, post_id),
        json={"content": "x" * 501},
        headers=auth_headers(tokens),
    )

    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_create_comment_on_missing_post_404(
    client: AsyncClient, fastapi_app: FastAPI
) -> None:
    _, tokens = await register_and_login(client, fastapi_app, "commenter-5")

    resp = await client.post(
        await _post_comments_url(fastapi_app, 999_999),
        json={"content": "hi"},
        headers=auth_headers(tokens),
    )

    assert resp.status_code == status.HTTP_404_NOT_FOUND


async def test_create_comment_on_others_on_moderation_404(
    client: AsyncClient, fastapi_app: FastAPI
) -> None:
    _, author_tokens = await register_and_login(client, fastapi_app, "author-6")
    post_id = await create_post_via_api(client, fastapi_app, author_tokens)
    _, viewer_tokens = await register_and_login(client, fastapi_app, "viewer-6")

    resp = await client.post(
        await _post_comments_url(fastapi_app, post_id),
        json={"content": "hi"},
        headers=auth_headers(viewer_tokens),
    )

    assert resp.status_code == status.HTTP_404_NOT_FOUND
