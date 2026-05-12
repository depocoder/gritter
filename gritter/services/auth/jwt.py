"""Access-token JWT encode/decode."""

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from gritter.settings import settings


class InvalidTokenError(Exception):
    """Raised when an access token cannot be decoded or is expired."""


def encode_access_token(user_id: int) -> str:
    """Issue a short-lived access token for `user_id`."""
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(
            (now + timedelta(seconds=settings.access_token_ttl_seconds)).timestamp()
        ),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> int:
    """Decode `token` and return its `user_id`. Raises InvalidTokenError on failure."""
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc

    if payload.get("type") != "access":
        raise InvalidTokenError("wrong token type")

    try:
        return int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidTokenError("missing or invalid sub") from exc
