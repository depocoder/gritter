from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from gritter.db.models.posts import Post, PostStatus
from tests.posts.helpers import auth_headers, register_and_login


async def _create_published(dbsession: AsyncSession, user_id: int) -> Post:
    p = Post(user_id=user_id, title="t", content="c", status=PostStatus.published)
    dbsession.add(p)
    await dbsession.flush()
    return p


async def test_delete_own_post_marks_soft_deleted(
    client: AsyncClient,
    fastapi_app: FastAPI,
    dbsession: AsyncSession,
) -> None:
    author, tokens = await register_and_login(client, fastapi_app, "del-own")
    p = await _create_published(dbsession, author["id"])

    url = fastapi_app.url_path_for("delete_post", post_id=p.id)
    resp = await client.delete(url, headers=auth_headers(tokens))

    assert resp.status_code == status.HTTP_204_NO_CONTENT
    refreshed = (
        await dbsession.execute(select(Post).where(Post.id == p.id))
    ).scalar_one()
    assert refreshed.deleted_at is not None


async def test_delete_other_users_post_is_403(
    client: AsyncClient,
    fastapi_app: FastAPI,
    dbsession: AsyncSession,
) -> None:
    author, _ = await register_and_login(client, fastapi_app, "del-not-mine")
    _, viewer_tokens = await register_and_login(client, fastapi_app, "del-viewer")
    p = await _create_published(dbsession, author["id"])

    url = fastapi_app.url_path_for("delete_post", post_id=p.id)
    resp = await client.delete(url, headers=auth_headers(viewer_tokens))

    assert resp.status_code == status.HTTP_403_FORBIDDEN


async def test_delete_unknown_post_is_404(
    client: AsyncClient, fastapi_app: FastAPI
) -> None:
    _, tokens = await register_and_login(client, fastapi_app, "del-unknown")

    url = fastapi_app.url_path_for("delete_post", post_id=10**9)
    resp = await client.delete(url, headers=auth_headers(tokens))

    assert resp.status_code == status.HTTP_404_NOT_FOUND


async def test_delete_requires_auth(client: AsyncClient, fastapi_app: FastAPI) -> None:
    url = fastapi_app.url_path_for("delete_post", post_id=1)
    resp = await client.delete(url)

    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


async def test_deleted_post_hidden_from_public_list(
    client: AsyncClient,
    fastapi_app: FastAPI,
    dbsession: AsyncSession,
) -> None:
    author, tokens = await register_and_login(client, fastapi_app, "del-hidden")
    p = await _create_published(dbsession, author["id"])
    await client.delete(
        fastapi_app.url_path_for("delete_post", post_id=p.id),
        headers=auth_headers(tokens),
    )

    resp = await client.get(fastapi_app.url_path_for("list_posts"))

    assert resp.json()["total"] == 0
