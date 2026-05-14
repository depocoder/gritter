from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from gritter.db.models.posts import Post, PostStatus
from gritter.db.models.posts_outbox import POST_UPDATED_EVENT, PostOutbox
from tests.posts.helpers import auth_headers, register_and_login


async def _create_published(
    dbsession: AsyncSession, user_id: int, *, title: str = "t", content: str = "c"
) -> Post:
    p = Post(
        user_id=user_id,
        title=title,
        content=content,
        status=PostStatus.published,
    )
    dbsession.add(p)
    await dbsession.flush()
    return p


async def test_update_content_resets_to_on_moderation_and_enqueues(
    client: AsyncClient,
    fastapi_app: FastAPI,
    dbsession: AsyncSession,
) -> None:
    author, tokens = await register_and_login(client, fastapi_app, "upd-content")
    p = await _create_published(dbsession, author["id"])

    url = fastapi_app.url_path_for("update_post", post_id=p.id)
    resp = await client.patch(
        url, json={"content": "new"}, headers=auth_headers(tokens)
    )

    assert resp.status_code == status.HTTP_200_OK
    body = resp.json()
    assert body["status"] == PostStatus.on_moderation.value
    assert body["content"] == "new"
    rows = (
        (
            await dbsession.execute(
                select(PostOutbox).where(PostOutbox.aggregate_id == p.id)
            )
        )
        .scalars()
        .all()
    )
    assert any(r.event_type == POST_UPDATED_EVENT for r in rows)


async def test_update_only_category_keeps_published_no_outbox(
    client: AsyncClient,
    fastapi_app: FastAPI,
    dbsession: AsyncSession,
) -> None:
    author, tokens = await register_and_login(client, fastapi_app, "upd-cat-only")
    p = await _create_published(dbsession, author["id"])

    url = fastapi_app.url_path_for("update_post", post_id=p.id)
    resp = await client.patch(
        url, json={"category": "news"}, headers=auth_headers(tokens)
    )

    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["status"] == PostStatus.published.value
    rows = (
        (
            await dbsession.execute(
                select(PostOutbox).where(PostOutbox.aggregate_id == p.id)
            )
        )
        .scalars()
        .all()
    )
    assert rows == []


async def test_update_rejects_long_content(
    client: AsyncClient,
    fastapi_app: FastAPI,
    dbsession: AsyncSession,
) -> None:
    author, tokens = await register_and_login(client, fastapi_app, "upd-too-long")
    p = await _create_published(dbsession, author["id"])

    url = fastapi_app.url_path_for("update_post", post_id=p.id)
    resp = await client.patch(
        url, json={"content": "x" * 281}, headers=auth_headers(tokens)
    )

    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_update_other_users_post_is_403(
    client: AsyncClient,
    fastapi_app: FastAPI,
    dbsession: AsyncSession,
) -> None:
    author, _ = await register_and_login(client, fastapi_app, "upd-not-author")
    _, viewer_tokens = await register_and_login(client, fastapi_app, "upd-viewer")
    p = await _create_published(dbsession, author["id"])

    url = fastapi_app.url_path_for("update_post", post_id=p.id)
    resp = await client.patch(
        url, json={"content": "x"}, headers=auth_headers(viewer_tokens)
    )

    assert resp.status_code == status.HTTP_403_FORBIDDEN


async def test_update_unknown_post_is_404(
    client: AsyncClient, fastapi_app: FastAPI
) -> None:
    _, tokens = await register_and_login(client, fastapi_app, "upd-unknown")

    url = fastapi_app.url_path_for("update_post", post_id=10**9)
    resp = await client.patch(url, json={"content": "x"}, headers=auth_headers(tokens))

    assert resp.status_code == status.HTTP_404_NOT_FOUND


async def test_update_requires_auth(client: AsyncClient, fastapi_app: FastAPI) -> None:
    url = fastapi_app.url_path_for("update_post", post_id=1)
    resp = await client.patch(url, json={"content": "x"})

    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


async def test_update_with_same_title_does_not_re_enqueue(
    client: AsyncClient,
    fastapi_app: FastAPI,
    dbsession: AsyncSession,
) -> None:
    author, tokens = await register_and_login(client, fastapi_app, "upd-same")
    p = await _create_published(dbsession, author["id"], title="orig")

    url = fastapi_app.url_path_for("update_post", post_id=p.id)
    resp = await client.patch(url, json={"title": "orig"}, headers=auth_headers(tokens))

    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["status"] == PostStatus.published.value
    rows = (
        (
            await dbsession.execute(
                select(PostOutbox).where(PostOutbox.aggregate_id == p.id)
            )
        )
        .scalars()
        .all()
    )
    assert rows == []
