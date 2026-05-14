from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from gritter.db.models.posts import Post, PostStatus
from gritter.db.models.posts_outbox import (
    POST_CREATED_EVENT,
    OutboxStatus,
    PostOutbox,
)
from tests.posts.helpers import auth_headers, register_and_login

VALID_BODY = {"title": "hello", "content": "world", "category": "news"}


async def test_create_post_returns_id_and_moderation_status(
    client: AsyncClient, fastapi_app: FastAPI
) -> None:
    _, tokens = await register_and_login(client, fastapi_app, "post-create")

    url = fastapi_app.url_path_for("create_post")
    resp = await client.post(url, json=VALID_BODY, headers=auth_headers(tokens))

    assert resp.status_code == status.HTTP_201_CREATED
    body = resp.json()
    assert body["id"] > 0
    assert body["status"] == PostStatus.on_moderation.value
    assert body["moderation_message"]


async def test_create_post_writes_outbox_row(
    client: AsyncClient,
    fastapi_app: FastAPI,
    dbsession: AsyncSession,
) -> None:
    _, tokens = await register_and_login(client, fastapi_app, "post-outbox")
    url = fastapi_app.url_path_for("create_post")
    resp = await client.post(url, json=VALID_BODY, headers=auth_headers(tokens))
    post_id = resp.json()["id"]

    rows = (
        (
            await dbsession.execute(
                select(PostOutbox).where(PostOutbox.aggregate_id == post_id)
            )
        )
        .scalars()
        .all()
    )

    assert len(rows) == 1
    assert rows[0].event_type == POST_CREATED_EVENT
    assert rows[0].status == OutboxStatus.pending


async def test_create_post_persists_post_row_on_moderation(
    client: AsyncClient, fastapi_app: FastAPI, dbsession: AsyncSession
) -> None:
    _, tokens = await register_and_login(client, fastapi_app, "post-row")
    url = fastapi_app.url_path_for("create_post")
    resp = await client.post(url, json=VALID_BODY, headers=auth_headers(tokens))
    post_id = resp.json()["id"]

    post = (
        await dbsession.execute(select(Post).where(Post.id == post_id))
    ).scalar_one()

    assert post.status == PostStatus.on_moderation
    assert post.title == "hello"
    assert post.content == "world"
    assert post.category == "news"


async def test_create_post_requires_auth(
    client: AsyncClient, fastapi_app: FastAPI
) -> None:
    url = fastapi_app.url_path_for("create_post")
    resp = await client.post(url, json=VALID_BODY)

    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


async def test_create_post_rejects_long_content(
    client: AsyncClient, fastapi_app: FastAPI
) -> None:
    _, tokens = await register_and_login(client, fastapi_app, "post-too-long")

    url = fastapi_app.url_path_for("create_post")
    resp = await client.post(
        url,
        json={"title": "t", "content": "x" * 281, "category": None},
        headers=auth_headers(tokens),
    )

    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_create_post_rejects_empty_title(
    client: AsyncClient, fastapi_app: FastAPI
) -> None:
    _, tokens = await register_and_login(client, fastapi_app, "post-empty-title")

    url = fastapi_app.url_path_for("create_post")
    resp = await client.post(
        url,
        json={"title": "", "content": "c", "category": None},
        headers=auth_headers(tokens),
    )

    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_create_post_accepts_null_category(
    client: AsyncClient, fastapi_app: FastAPI
) -> None:
    _, tokens = await register_and_login(client, fastapi_app, "post-null-cat")

    url = fastapi_app.url_path_for("create_post")
    resp = await client.post(
        url,
        json={"title": "t", "content": "c"},
        headers=auth_headers(tokens),
    )

    assert resp.status_code == status.HTTP_201_CREATED
