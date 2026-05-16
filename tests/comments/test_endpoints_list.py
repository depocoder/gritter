"""HTTP-level tests for ``GET /api/posts/{id}/comments`` (US-3.3)."""

from datetime import datetime, timedelta
from typing import Any

from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from gritter.db.models.comments import Comment
from tests.comments.helpers import (
    auth_headers,
    create_post_via_api,
    publish_post,
    register_and_login,
)


async def _list_url(app: FastAPI, post_id: int, **query: Any) -> str:
    base = app.url_path_for("list_comments", post_id=post_id)
    if not query:
        return base
    qs = "&".join(f"{k}={v}" for k, v in query.items())
    return f"{base}?{qs}"


async def _seed_comments(
    dbsession: AsyncSession,
    *,
    post_id: int,
    author_id: int,
    n: int,
) -> list[Comment]:
    """Insert ``n`` comments with strictly increasing ``created_at``."""
    base = datetime(2026, 5, 16, 12, 0, 0)
    rows = [
        Comment(
            post_id=post_id,
            user_id=author_id,
            content=f"c-{i}",
            created_at=base + timedelta(seconds=i),
        )
        for i in range(n)
    ]
    dbsession.add_all(rows)
    await dbsession.flush()
    return rows


async def test_list_returns_oldest_first_with_pagination(
    client: AsyncClient, fastapi_app: FastAPI, dbsession: AsyncSession
) -> None:
    user_json, tokens = await register_and_login(client, fastapi_app, "lister-1")
    post_id = await create_post_via_api(client, fastapi_app, tokens)
    await publish_post(dbsession, post_id)
    await _seed_comments(dbsession, post_id=post_id, author_id=user_json["id"], n=3)

    resp = await client.get(await _list_url(fastapi_app, post_id, page=1, size=2))

    assert resp.status_code == status.HTTP_200_OK
    body = resp.json()
    assert body["total"] == 3
    assert body["page"] == 1
    assert body["size"] == 2
    assert body["has_next"] is True
    assert [item["content"] for item in body["items"]] == ["c-0", "c-1"]


async def test_list_default_size_is_ten(
    client: AsyncClient, fastapi_app: FastAPI, dbsession: AsyncSession
) -> None:
    user_json, tokens = await register_and_login(client, fastapi_app, "lister-2")
    post_id = await create_post_via_api(client, fastapi_app, tokens)
    await publish_post(dbsession, post_id)
    await _seed_comments(dbsession, post_id=post_id, author_id=user_json["id"], n=12)

    resp = await client.get(await _list_url(fastapi_app, post_id))

    body = resp.json()
    assert body["size"] == 10
    assert len(body["items"]) == 10
    assert body["has_next"] is True


async def test_list_rejects_oversized_page(
    client: AsyncClient, fastapi_app: FastAPI, dbsession: AsyncSession
) -> None:
    _, tokens = await register_and_login(client, fastapi_app, "lister-3")
    post_id = await create_post_via_api(client, fastapi_app, tokens)
    await publish_post(dbsession, post_id)

    resp = await client.get(await _list_url(fastapi_app, post_id, size=51))

    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_list_skips_soft_deleted_comments(
    client: AsyncClient, fastapi_app: FastAPI, dbsession: AsyncSession
) -> None:
    user_json, tokens = await register_and_login(client, fastapi_app, "lister-4")
    post_id = await create_post_via_api(client, fastapi_app, tokens)
    await publish_post(dbsession, post_id)
    rows = await _seed_comments(
        dbsession, post_id=post_id, author_id=user_json["id"], n=3
    )
    rows[1].deleted_at = datetime(2026, 5, 16, 13, 0, 0)
    await dbsession.flush()

    resp = await client.get(await _list_url(fastapi_app, post_id))

    body = resp.json()
    assert body["total"] == 2
    assert [item["content"] for item in body["items"]] == ["c-0", "c-2"]


async def test_list_on_missing_post_404(
    client: AsyncClient, fastapi_app: FastAPI
) -> None:
    resp = await client.get(await _list_url(fastapi_app, 999_999))

    assert resp.status_code == status.HTTP_404_NOT_FOUND


async def test_list_on_others_on_moderation_404(
    client: AsyncClient, fastapi_app: FastAPI
) -> None:
    _, author_tokens = await register_and_login(client, fastapi_app, "author-7")
    post_id = await create_post_via_api(client, fastapi_app, author_tokens)
    _, viewer_tokens = await register_and_login(client, fastapi_app, "viewer-7")

    resp = await client.get(
        await _list_url(fastapi_app, post_id), headers=auth_headers(viewer_tokens)
    )

    assert resp.status_code == status.HTTP_404_NOT_FOUND


async def test_list_anonymous_can_read_published(
    client: AsyncClient, fastapi_app: FastAPI, dbsession: AsyncSession
) -> None:
    _, tokens = await register_and_login(client, fastapi_app, "lister-8")
    post_id = await create_post_via_api(client, fastapi_app, tokens)
    await publish_post(dbsession, post_id)

    resp = await client.get(await _list_url(fastapi_app, post_id))

    assert resp.status_code == status.HTTP_200_OK
