"""HTTP-level tests for ``DELETE /api/comments/{id}`` (US-3.4)."""

from typing import Any

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


async def _create_comment(
    client: AsyncClient,
    app: FastAPI,
    tokens: dict[str, Any],
    post_id: int,
) -> int:
    url = app.url_path_for("create_comment", post_id=post_id)
    resp = await client.post(url, json={"content": "x"}, headers=auth_headers(tokens))
    assert resp.status_code == status.HTTP_201_CREATED, resp.text
    comment_id: int = resp.json()["id"]
    return comment_id


async def _delete_url(app: FastAPI, comment_id: int) -> str:
    return app.url_path_for("delete_comment", comment_id=comment_id)


async def test_comment_author_can_soft_delete(
    client: AsyncClient, fastapi_app: FastAPI, dbsession: AsyncSession
) -> None:
    _, tokens = await register_and_login(client, fastapi_app, "del-1")
    post_id = await create_post_via_api(client, fastapi_app, tokens)
    await publish_post(dbsession, post_id)
    comment_id = await _create_comment(client, fastapi_app, tokens, post_id)

    resp = await client.delete(
        await _delete_url(fastapi_app, comment_id), headers=auth_headers(tokens)
    )

    assert resp.status_code == status.HTTP_204_NO_CONTENT
    row = (
        await dbsession.execute(select(Comment).where(Comment.id == comment_id))
    ).scalar_one()
    assert row.deleted_at is not None
    post = (
        await dbsession.execute(select(Post).where(Post.id == post_id))
    ).scalar_one()
    assert post.comments_count == 0


async def test_post_author_can_delete_others_comment(
    client: AsyncClient, fastapi_app: FastAPI, dbsession: AsyncSession
) -> None:
    _, author_tokens = await register_and_login(client, fastapi_app, "post-author-2")
    post_id = await create_post_via_api(client, fastapi_app, author_tokens)
    await publish_post(dbsession, post_id)
    _, commenter_tokens = await register_and_login(client, fastapi_app, "commenter-2")
    comment_id = await _create_comment(client, fastapi_app, commenter_tokens, post_id)

    resp = await client.delete(
        await _delete_url(fastapi_app, comment_id),
        headers=auth_headers(author_tokens),
    )

    assert resp.status_code == status.HTTP_204_NO_CONTENT


async def test_third_party_cannot_delete_comment(
    client: AsyncClient, fastapi_app: FastAPI, dbsession: AsyncSession
) -> None:
    _, post_author = await register_and_login(client, fastapi_app, "p-author-3")
    post_id = await create_post_via_api(client, fastapi_app, post_author)
    await publish_post(dbsession, post_id)
    _, commenter = await register_and_login(client, fastapi_app, "commenter-3")
    comment_id = await _create_comment(client, fastapi_app, commenter, post_id)
    _, stranger = await register_and_login(client, fastapi_app, "stranger-3")

    resp = await client.delete(
        await _delete_url(fastapi_app, comment_id), headers=auth_headers(stranger)
    )

    assert resp.status_code == status.HTTP_403_FORBIDDEN


async def test_delete_already_deleted_comment_404(
    client: AsyncClient, fastapi_app: FastAPI, dbsession: AsyncSession
) -> None:
    _, tokens = await register_and_login(client, fastapi_app, "del-4")
    post_id = await create_post_via_api(client, fastapi_app, tokens)
    await publish_post(dbsession, post_id)
    comment_id = await _create_comment(client, fastapi_app, tokens, post_id)

    first = await client.delete(
        await _delete_url(fastapi_app, comment_id), headers=auth_headers(tokens)
    )
    second = await client.delete(
        await _delete_url(fastapi_app, comment_id), headers=auth_headers(tokens)
    )

    assert first.status_code == status.HTTP_204_NO_CONTENT
    assert second.status_code == status.HTTP_404_NOT_FOUND


async def test_delete_decrements_counter_exactly_once(
    client: AsyncClient, fastapi_app: FastAPI, dbsession: AsyncSession
) -> None:
    """Double-DELETE must not drive ``comments_count`` below zero."""
    _, tokens = await register_and_login(client, fastapi_app, "del-5")
    post_id = await create_post_via_api(client, fastapi_app, tokens)
    await publish_post(dbsession, post_id)
    comment_id = await _create_comment(client, fastapi_app, tokens, post_id)

    await client.delete(
        await _delete_url(fastapi_app, comment_id), headers=auth_headers(tokens)
    )
    await client.delete(
        await _delete_url(fastapi_app, comment_id), headers=auth_headers(tokens)
    )

    post = (
        await dbsession.execute(select(Post).where(Post.id == post_id))
    ).scalar_one()
    assert post.comments_count == 0


async def test_delete_requires_auth(
    client: AsyncClient, fastapi_app: FastAPI, dbsession: AsyncSession
) -> None:
    _, tokens = await register_and_login(client, fastapi_app, "del-6")
    post_id = await create_post_via_api(client, fastapi_app, tokens)
    await publish_post(dbsession, post_id)
    comment_id = await _create_comment(client, fastapi_app, tokens, post_id)

    resp = await client.delete(await _delete_url(fastapi_app, comment_id))

    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
