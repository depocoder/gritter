from typing import Any
from unittest.mock import Mock

from fastapi import FastAPI
from httpx import AsyncClient
from minio.error import S3Error
from starlette import status

from tests.profile.helpers import auth_headers, register_and_login


async def test_get_my_profile_returns_current_user(
    client: AsyncClient, fastapi_app: FastAPI
) -> None:
    user, tokens = await register_and_login(client, fastapi_app, "prof-self")

    url = fastapi_app.url_path_for("get_my_profile")
    resp = await client.get(url, headers=auth_headers(tokens))

    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["id"] == user["id"]
    assert resp.json()["login"] == "prof-self"


async def test_upload_avatar_writes_url_and_object(
    client: AsyncClient, fastapi_app: FastAPI, test_minio_client: Mock
) -> None:
    user, tokens = await register_and_login(client, fastapi_app, "av-upload")

    url = fastapi_app.url_path_for("upload_my_avatar")
    resp = await client.post(
        url,
        headers=auth_headers(tokens),
        files={"file": ("a.png", b"PNGDATA", "image/png")},
    )

    assert resp.status_code == status.HTTP_200_OK, resp.text
    body = resp.json()
    assert body["avatar_url"] == f"/api/avatars/users/{user['id']}/avatar.png"
    assert f"users/{user['id']}/avatar.png" in test_minio_client._store


async def test_upload_avatar_rejects_unsupported_mime(
    client: AsyncClient, fastapi_app: FastAPI
) -> None:
    _, tokens = await register_and_login(client, fastapi_app, "av-mime")

    url = fastapi_app.url_path_for("upload_my_avatar")
    resp = await client.post(
        url,
        headers=auth_headers(tokens),
        files={"file": ("a.gif", b"GIF", "image/gif")},
    )

    assert resp.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE


async def test_upload_avatar_rejects_too_large(
    client: AsyncClient, fastapi_app: FastAPI
) -> None:
    _, tokens = await register_and_login(client, fastapi_app, "av-big")

    payload = b"\x00" * (2 * 1024 * 1024 + 1)
    url = fastapi_app.url_path_for("upload_my_avatar")
    resp = await client.post(
        url,
        headers=auth_headers(tokens),
        files={"file": ("a.png", payload, "image/png")},
    )

    assert resp.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE


async def test_upload_avatar_requires_auth(
    client: AsyncClient, fastapi_app: FastAPI
) -> None:
    url = fastapi_app.url_path_for("upload_my_avatar")
    resp = await client.post(url, files={"file": ("a.png", b"x", "image/png")})

    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


async def test_serve_avatar_returns_stored_bytes_and_content_type(
    client: AsyncClient, fastapi_app: FastAPI
) -> None:
    _, tokens = await register_and_login(client, fastapi_app, "av-serve")
    upload = await client.post(
        fastapi_app.url_path_for("upload_my_avatar"),
        headers=auth_headers(tokens),
        files={"file": ("a.webp", b"WEBPBYTES", "image/webp")},
    )
    avatar_url = upload.json()["avatar_url"]

    resp = await client.get(avatar_url)

    assert resp.status_code == status.HTTP_200_OK
    assert resp.content == b"WEBPBYTES"
    assert resp.headers["content-type"] == "image/webp"


async def test_serve_avatar_404_on_missing_object(
    client: AsyncClient, fastapi_app: FastAPI
) -> None:
    resp = await client.get("/api/avatars/users/999999/avatar.png")

    assert resp.status_code == status.HTTP_404_NOT_FOUND


async def test_serve_avatar_propagates_unexpected_minio_errors(
    client: AsyncClient, fastapi_app: FastAPI, test_minio_client: Mock
) -> None:
    def boom(*_args: Any, **_kwargs: Any) -> None:
        raise S3Error(
            code="InternalError",
            message="boom",
            resource="x",
            request_id="x",
            host_id="x",
            response=Mock(),
        )

    test_minio_client.get_object.side_effect = boom

    resp = await client.get("/api/avatars/anything")

    assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


async def test_serve_avatar_500s_on_generic_minio_exception(
    client: AsyncClient, fastapi_app: FastAPI, test_minio_client: Mock
) -> None:
    from minio.error import MinioException

    def boom(*_args: Any, **_kwargs: Any) -> None:
        raise MinioException("connection reset")

    test_minio_client.get_object.side_effect = boom

    resp = await client.get("/api/avatars/anything")

    assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
