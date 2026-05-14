from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from gritter.db.models.posts import Post, PostStatus
from tests.posts.helpers import auth_headers, register_and_login


async def test_my_posts_returns_all_statuses_for_author(
    client: AsyncClient,
    fastapi_app: FastAPI,
    dbsession: AsyncSession,
) -> None:
    author, tokens = await register_and_login(client, fastapi_app, "my-all")
    dbsession.add_all(
        [
            Post(user_id=author["id"], title="mod", content="c"),
            Post(
                user_id=author["id"],
                title="pub",
                content="c",
                status=PostStatus.published,
            ),
        ]
    )
    await dbsession.flush()

    url = fastapi_app.url_path_for("list_my_posts")
    resp = await client.get(url, headers=auth_headers(tokens))

    titles = sorted(item["title"] for item in resp.json()["items"])
    assert titles == ["mod", "pub"]


async def test_my_posts_filters_by_status(
    client: AsyncClient,
    fastapi_app: FastAPI,
    dbsession: AsyncSession,
) -> None:
    author, tokens = await register_and_login(client, fastapi_app, "my-status")
    dbsession.add_all(
        [
            Post(user_id=author["id"], title="mod", content="c"),
            Post(
                user_id=author["id"],
                title="pub",
                content="c",
                status=PostStatus.published,
            ),
        ]
    )
    await dbsession.flush()

    url = fastapi_app.url_path_for("list_my_posts")
    resp = await client.get(
        url,
        params={"status": PostStatus.on_moderation.value},
        headers=auth_headers(tokens),
    )

    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["title"] == "mod"
    assert items[0]["is_on_moderation"] is True


async def test_my_posts_marks_published_as_not_on_moderation(
    client: AsyncClient,
    fastapi_app: FastAPI,
    dbsession: AsyncSession,
) -> None:
    author, tokens = await register_and_login(client, fastapi_app, "my-flag")
    dbsession.add(
        Post(
            user_id=author["id"],
            title="pub",
            content="c",
            status=PostStatus.published,
        )
    )
    await dbsession.flush()

    url = fastapi_app.url_path_for("list_my_posts")
    resp = await client.get(url, headers=auth_headers(tokens))

    assert resp.json()["items"][0]["is_on_moderation"] is False


async def test_my_posts_excludes_soft_deleted(
    client: AsyncClient,
    fastapi_app: FastAPI,
    dbsession: AsyncSession,
) -> None:
    author, tokens = await register_and_login(client, fastapi_app, "my-deleted")
    p = Post(
        user_id=author["id"],
        title="t",
        content="c",
        status=PostStatus.published,
    )
    dbsession.add(p)
    await dbsession.flush()
    await client.delete(
        fastapi_app.url_path_for("delete_post", post_id=p.id),
        headers=auth_headers(tokens),
    )

    resp = await client.get(
        fastapi_app.url_path_for("list_my_posts"), headers=auth_headers(tokens)
    )

    assert resp.json()["total"] == 0


async def test_my_posts_requires_auth(
    client: AsyncClient, fastapi_app: FastAPI
) -> None:
    url = fastapi_app.url_path_for("list_my_posts")
    resp = await client.get(url)

    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


async def test_my_posts_does_not_show_other_users_posts(
    client: AsyncClient,
    fastapi_app: FastAPI,
    dbsession: AsyncSession,
) -> None:
    author, _ = await register_and_login(client, fastapi_app, "my-other-author")
    _, viewer_tokens = await register_and_login(client, fastapi_app, "my-viewer")
    dbsession.add(
        Post(
            user_id=author["id"],
            title="t",
            content="c",
            status=PostStatus.published,
        )
    )
    await dbsession.flush()

    resp = await client.get(
        fastapi_app.url_path_for("list_my_posts"),
        headers=auth_headers(viewer_tokens),
    )

    assert resp.json()["total"] == 0
