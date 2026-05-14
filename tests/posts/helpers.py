"""Shared helpers for posts-epic tests."""

from typing import Any

from fastapi import FastAPI
from httpx import AsyncClient
from starlette import status

DEFAULT_PASSWORD = "compiler-1952"


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
