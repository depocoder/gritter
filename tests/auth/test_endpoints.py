from typing import Any

from fastapi import FastAPI
from httpx import AsyncClient
from starlette import status

from gritter.services.auth.jwt import encode_access_token


def _register_payload(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "first_name": "Grace",
        "last_name": "Hopper",
        "login": "grace",
        "password": "compiler-1952",
    }
    base.update(overrides)
    return base


async def _register(
    client: AsyncClient, app: FastAPI, **overrides: Any
) -> dict[str, Any]:
    url = app.url_path_for("register")
    resp = await client.post(url, json=_register_payload(**overrides))
    assert resp.status_code == status.HTTP_201_CREATED, resp.text
    return resp.json()


async def _login(
    client: AsyncClient, app: FastAPI, login: str, password: str
) -> dict[str, Any]:
    url = app.url_path_for("login")
    resp = await client.post(url, json={"login": login, "password": password})
    assert resp.status_code == status.HTTP_200_OK, resp.text
    return resp.json()


async def test_register_creates_user(client: AsyncClient, fastapi_app: FastAPI) -> None:
    body = await _register(client, fastapi_app)
    assert body["login"] == "grace"
    assert body["first_name"] == "Grace"
    assert "password" not in body
    assert "password_hash" not in body
    assert body["id"] > 0


async def test_register_rejects_duplicate_login(
    client: AsyncClient, fastapi_app: FastAPI
) -> None:
    await _register(client, fastapi_app, login="dupe")
    url = fastapi_app.url_path_for("register")
    resp = await client.post(url, json=_register_payload(login="dupe"))
    assert resp.status_code == status.HTTP_409_CONFLICT


async def test_register_validates_short_login(
    client: AsyncClient, fastapi_app: FastAPI
) -> None:
    url = fastapi_app.url_path_for("register")
    resp = await client.post(url, json=_register_payload(login="ab"))
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_register_validates_short_password(
    client: AsyncClient, fastapi_app: FastAPI
) -> None:
    url = fastapi_app.url_path_for("register")
    resp = await client.post(url, json=_register_payload(password="short"))
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_login_returns_token_pair(
    client: AsyncClient, fastapi_app: FastAPI
) -> None:
    await _register(client, fastapi_app, login="logintest")
    tokens = await _login(client, fastapi_app, "logintest", "compiler-1952")
    assert tokens["access_token"]
    assert tokens["refresh_token"]
    assert tokens["token_type"] == "bearer"


async def test_login_rejects_unknown_user(
    client: AsyncClient, fastapi_app: FastAPI
) -> None:
    url = fastapi_app.url_path_for("login")
    resp = await client.post(url, json={"login": "nobody", "password": "whatever1"})
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


async def test_login_rejects_wrong_password(
    client: AsyncClient, fastapi_app: FastAPI
) -> None:
    await _register(client, fastapi_app, login="wrongpw")
    url = fastapi_app.url_path_for("login")
    resp = await client.post(
        url, json={"login": "wrongpw", "password": "not-the-password"}
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


async def test_refresh_rotates_tokens(
    client: AsyncClient, fastapi_app: FastAPI
) -> None:
    await _register(client, fastapi_app, login="refresher")
    first = await _login(client, fastapi_app, "refresher", "compiler-1952")

    url = fastapi_app.url_path_for("refresh")
    resp = await client.post(url, json={"refresh_token": first["refresh_token"]})
    assert resp.status_code == status.HTTP_200_OK
    rotated = resp.json()
    assert rotated["refresh_token"] != first["refresh_token"]

    # Old refresh is now invalid (single-use)
    resp_again = await client.post(url, json={"refresh_token": first["refresh_token"]})
    assert resp_again.status_code == status.HTTP_401_UNAUTHORIZED


async def test_refresh_rejects_unknown_token(
    client: AsyncClient, fastapi_app: FastAPI
) -> None:
    url = fastapi_app.url_path_for("refresh")
    resp = await client.post(url, json={"refresh_token": "nope"})
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


async def test_change_password_happy_path(
    client: AsyncClient, fastapi_app: FastAPI
) -> None:
    await _register(client, fastapi_app, login="changepw1")
    tokens = await _login(client, fastapi_app, "changepw1", "compiler-1952")

    url = fastapi_app.url_path_for("change_password")
    resp = await client.post(
        url,
        json={"old_password": "compiler-1952", "new_password": "brand-new-pw-9000"},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert resp.status_code == status.HTTP_204_NO_CONTENT

    # Old password no longer works
    login_url = fastapi_app.url_path_for("login")
    bad = await client.post(
        login_url, json={"login": "changepw1", "password": "compiler-1952"}
    )
    assert bad.status_code == status.HTTP_401_UNAUTHORIZED

    # New password does
    good = await client.post(
        login_url,
        json={"login": "changepw1", "password": "brand-new-pw-9000"},
    )
    assert good.status_code == status.HTTP_200_OK


async def test_change_password_rejects_wrong_old(
    client: AsyncClient, fastapi_app: FastAPI
) -> None:
    await _register(client, fastapi_app, login="changepw2")
    tokens = await _login(client, fastapi_app, "changepw2", "compiler-1952")

    url = fastapi_app.url_path_for("change_password")
    resp = await client.post(
        url,
        json={"old_password": "not-the-old", "new_password": "brand-new-pw-9000"},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


async def test_change_password_requires_auth(
    client: AsyncClient, fastapi_app: FastAPI
) -> None:
    url = fastapi_app.url_path_for("change_password")
    resp = await client.post(
        url,
        json={"old_password": "a", "new_password": "brand-new-pw-9000"},
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


async def test_change_password_rejects_bad_jwt(
    client: AsyncClient, fastapi_app: FastAPI
) -> None:
    url = fastapi_app.url_path_for("change_password")
    resp = await client.post(
        url,
        json={"old_password": "a", "new_password": "brand-new-pw-9000"},
        headers={"Authorization": "Bearer not.a.jwt"},
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


async def test_change_password_rejects_token_for_missing_user(
    client: AsyncClient, fastapi_app: FastAPI
) -> None:
    """Token is well-formed but its user does not exist in DB."""
    token = encode_access_token(user_id=10**9)
    url = fastapi_app.url_path_for("change_password")
    resp = await client.post(
        url,
        json={"old_password": "a", "new_password": "brand-new-pw-9000"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


async def test_change_password_rejects_non_bearer_scheme(
    client: AsyncClient, fastapi_app: FastAPI
) -> None:
    url = fastapi_app.url_path_for("change_password")
    resp = await client.post(
        url,
        json={"old_password": "a", "new_password": "brand-new-pw-9000"},
        headers={"Authorization": "Basic dXNlcjpwYXNz"},
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
