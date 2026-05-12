"""Refresh tokens with rotation, stored hashed in Redis."""

import hashlib
import secrets

from redis.asyncio import Redis

from gritter.settings import settings

REFRESH_KEY_PREFIX = "refresh:"


def _hash_token(token: str) -> str:
    """Hash a refresh token for storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _key(token: str) -> str:
    return f"{REFRESH_KEY_PREFIX}{_hash_token(token)}"


async def issue_refresh_token(redis: Redis, user_id: int) -> str:
    """Create a new opaque refresh token, store its hash in Redis, return the token."""
    token = secrets.token_urlsafe(48)
    await redis.set(_key(token), str(user_id), ex=settings.refresh_token_ttl_seconds)
    return token


async def consume_refresh_token(redis: Redis, token: str) -> int | None:
    """Atomically read+delete a refresh token. Returns user_id, or None if invalid."""
    key = _key(token)
    pipe = redis.pipeline()
    pipe.get(key)
    pipe.delete(key)
    raw_user_id, _deleted = await pipe.execute()
    if raw_user_id is None:
        return None
    if isinstance(raw_user_id, bytes):
        raw_user_id = raw_user_id.decode("utf-8")
    try:
        return int(raw_user_id)
    except (TypeError, ValueError):
        return None
