"""Shared helpers for comments-epic tests."""

from typing import Any

from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from gritter.db.models.posts import Post, PostStatus

DEFAULT_PASSWORD = "compiler-1952"
VALID_POST_BODY = {"title": "hello", "content": "world", "category": "news"}


def register_payload(login: str, **overrides: Any) -> dict[str, Any]:
    """Build a `RegisterIn` body, defaulting to a usable user."""
    base: dict[str, Any] = {
        "first_name": "Grace",
        "last_name": "Hopper",
        "login": login,
        "password": DEFAULT_PASSWORD,
    }
    base.update(overrides)
    return base


async def register_and_login(
    client: AsyncClient, app: FastAPI, login: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Register a fresh user and return `(user_json, tokens_json)`."""
    reg_url = app.url_path_for("register")
    reg = await client.post(reg_url, json=register_payload(login))
    assert reg.status_code == status.HTTP_201_CREATED, reg.text

    login_url = app.url_path_for("login")
    log = await client.post(
        login_url, json={"login": login, "password": DEFAULT_PASSWORD}
    )
    assert log.status_code == status.HTTP_200_OK, log.text
    return reg.json(), log.json()


def auth_headers(tokens: dict[str, Any]) -> dict[str, str]:
    """Build a Bearer-token header dict from a token-pair payload."""
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def create_post_via_api(
    client: AsyncClient,
    app: FastAPI,
    tokens: dict[str, Any],
    *,
    body: dict[str, Any] | None = None,
) -> int:
    """Create a post through ``POST /api/posts`` and return its ID."""
    url = app.url_path_for("create_post")
    resp = await client.post(
        url, json=body or VALID_POST_BODY, headers=auth_headers(tokens)
    )
    assert resp.status_code == status.HTTP_201_CREATED, resp.text
    post_id: int = resp.json()["id"]
    return post_id


async def publish_post(dbsession: AsyncSession, post_id: int) -> None:
    """Flip ``posts.status`` to ``published`` so non-authors can interact."""
    await dbsession.execute(
        update(Post).where(Post.id == post_id).values(status=PostStatus.published)
    )
    await dbsession.flush()
