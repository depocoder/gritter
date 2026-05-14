from fastapi import FastAPI
from httpx import AsyncClient
from starlette import status

from tests.profile.helpers import auth_headers, register_and_login


async def test_follow_creates_edge(client: AsyncClient, fastapi_app: FastAPI) -> None:
    me, my_tokens = await register_and_login(client, fastapi_app, "fol-me")
    them, _ = await register_and_login(client, fastapi_app, "fol-them")

    url = fastapi_app.url_path_for("follow_user", user_id=them["id"])
    resp = await client.post(url, headers=auth_headers(my_tokens))

    assert resp.status_code == status.HTTP_201_CREATED
    body = resp.json()
    assert body["follower_id"] == me["id"]
    assert body["followee_id"] == them["id"]


async def test_follow_self_is_400(client: AsyncClient, fastapi_app: FastAPI) -> None:
    me, my_tokens = await register_and_login(client, fastapi_app, "fol-self")

    url = fastapi_app.url_path_for("follow_user", user_id=me["id"])
    resp = await client.post(url, headers=auth_headers(my_tokens))

    assert resp.status_code == status.HTTP_400_BAD_REQUEST


async def test_follow_unknown_user_is_404(
    client: AsyncClient, fastapi_app: FastAPI
) -> None:
    _, my_tokens = await register_and_login(client, fastapi_app, "fol-unknown")

    url = fastapi_app.url_path_for("follow_user", user_id=10**9)
    resp = await client.post(url, headers=auth_headers(my_tokens))

    assert resp.status_code == status.HTTP_404_NOT_FOUND


async def test_follow_duplicate_is_409(
    client: AsyncClient, fastapi_app: FastAPI
) -> None:
    _, my_tokens = await register_and_login(client, fastapi_app, "fol-dup-me")
    them, _ = await register_and_login(client, fastapi_app, "fol-dup-them")
    url = fastapi_app.url_path_for("follow_user", user_id=them["id"])
    first = await client.post(url, headers=auth_headers(my_tokens))
    assert first.status_code == status.HTTP_201_CREATED

    second = await client.post(url, headers=auth_headers(my_tokens))

    assert second.status_code == status.HTTP_409_CONFLICT


async def test_unfollow_removes_edge(client: AsyncClient, fastapi_app: FastAPI) -> None:
    _, my_tokens = await register_and_login(client, fastapi_app, "unf-me")
    them, _ = await register_and_login(client, fastapi_app, "unf-them")
    url = fastapi_app.url_path_for("follow_user", user_id=them["id"])
    await client.post(url, headers=auth_headers(my_tokens))

    unf_url = fastapi_app.url_path_for("unfollow_user", user_id=them["id"])
    resp = await client.delete(unf_url, headers=auth_headers(my_tokens))

    assert resp.status_code == status.HTTP_204_NO_CONTENT


async def test_unfollow_when_not_following_is_404(
    client: AsyncClient, fastapi_app: FastAPI
) -> None:
    _, my_tokens = await register_and_login(client, fastapi_app, "unf-nofollow")
    them, _ = await register_and_login(client, fastapi_app, "unf-target")

    url = fastapi_app.url_path_for("unfollow_user", user_id=them["id"])
    resp = await client.delete(url, headers=auth_headers(my_tokens))

    assert resp.status_code == status.HTTP_404_NOT_FOUND


async def test_follow_requires_auth(client: AsyncClient, fastapi_app: FastAPI) -> None:
    url = fastapi_app.url_path_for("follow_user", user_id=1)
    resp = await client.post(url)

    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
