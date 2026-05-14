"""Avatar storage helpers (MinIO put / get / public URL)."""

import asyncio
import io
from dataclasses import dataclass

from minio import Minio
from urllib3.response import BaseHTTPResponse

from gritter.settings import settings

MIME_TO_EXT: dict[str, str] = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}

ALLOWED_MIME_TYPES: frozenset[str] = frozenset(MIME_TO_EXT)
MAX_AVATAR_BYTES: int = 2 * 1024 * 1024


@dataclass(frozen=True)
class AvatarObject:
    """Bytes + content type for a fetched avatar."""

    data: bytes
    content_type: str


def object_key_for(user_id: int, content_type: str) -> str:
    """Compute the MinIO object key for a user's avatar."""
    ext = MIME_TO_EXT[content_type]
    return f"users/{user_id}/avatar.{ext}"


def public_url_for(object_key: str) -> str:
    """URL the API serves the avatar at (matches the `/api/avatars` route)."""
    return f"/api/avatars/{object_key}"


async def upload_avatar(
    client: Minio,
    *,
    object_key: str,
    data: bytes,
    content_type: str,
) -> None:
    """Put `data` to MinIO at `object_key` (sync SDK wrapped in to_thread)."""

    def _put() -> None:
        client.put_object(
            bucket_name=settings.minio_bucket_avatars,
            object_name=object_key,
            data=io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )

    await asyncio.to_thread(_put)


async def fetch_avatar(client: Minio, object_key: str) -> AvatarObject:
    """Get bytes + Content-Type for an avatar; raises on missing/IO error."""

    def _get() -> AvatarObject:
        response: BaseHTTPResponse = client.get_object(
            bucket_name=settings.minio_bucket_avatars,
            object_name=object_key,
        )
        try:
            data = response.read()
            content_type = response.headers.get("Content-Type", "image/jpeg")
            return AvatarObject(data=data, content_type=content_type)
        finally:
            response.close()
            response.release_conn()

    return await asyncio.to_thread(_get)
