from unittest.mock import Mock

import pytest

from gritter.services.avatar import (
    ALLOWED_MIME_TYPES,
    fetch_avatar,
    object_key_for,
    public_url_for,
    upload_avatar,
)


def test_object_key_for_uses_mime_extension() -> None:
    assert object_key_for(7, "image/png") == "users/7/avatar.png"
    assert object_key_for(42, "image/jpeg") == "users/42/avatar.jpg"
    assert object_key_for(99, "image/webp") == "users/99/avatar.webp"


def test_object_key_for_rejects_unknown_mime() -> None:
    with pytest.raises(KeyError):
        object_key_for(1, "image/gif")


def test_public_url_for_matches_route_prefix() -> None:
    key = object_key_for(7, "image/png")

    assert public_url_for(key) == "/api/avatars/users/7/avatar.png"


def test_allowed_mime_types_match_spec() -> None:
    assert frozenset({"image/jpeg", "image/png", "image/webp"}) == ALLOWED_MIME_TYPES


async def test_upload_avatar_calls_minio_with_metadata(
    test_minio_client: Mock,
) -> None:
    await upload_avatar(
        test_minio_client,
        object_key="users/7/avatar.png",
        data=b"PNGDATA",
        content_type="image/png",
    )

    test_minio_client.put_object.assert_called_once()
    kwargs = test_minio_client.put_object.call_args.kwargs
    assert kwargs["object_name"] == "users/7/avatar.png"
    assert kwargs["length"] == len(b"PNGDATA")
    assert kwargs["content_type"] == "image/png"


async def test_fetch_avatar_returns_data_and_content_type(
    test_minio_client: Mock,
) -> None:
    await upload_avatar(
        test_minio_client,
        object_key="users/9/avatar.webp",
        data=b"WEBP",
        content_type="image/webp",
    )

    avatar = await fetch_avatar(test_minio_client, "users/9/avatar.webp")

    assert avatar.data == b"WEBP"
    assert avatar.content_type == "image/webp"


def test_get_minio_client_dependency_reads_from_app_state(
    test_minio_client: Mock,
) -> None:
    from gritter.services.minio.dependency import get_minio_client

    request = Mock()
    request.app.state.minio_client = test_minio_client

    assert get_minio_client(request) is test_minio_client
