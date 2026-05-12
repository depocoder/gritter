import jwt as pyjwt
import pytest

from gritter.services.auth.jwt import (
    InvalidTokenError,
    decode_access_token,
    encode_access_token,
)
from gritter.settings import settings


def test_encode_then_decode_round_trip() -> None:
    token = encode_access_token(42)
    assert decode_access_token(token) == 42


def test_decode_rejects_garbage_string() -> None:
    with pytest.raises(InvalidTokenError):
        decode_access_token("definitely.not.jwt")


def test_decode_rejects_wrong_token_type() -> None:
    bad = pyjwt.encode(
        {"sub": "1", "type": "refresh"},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(InvalidTokenError, match="wrong token type"):
        decode_access_token(bad)


def test_decode_rejects_missing_sub() -> None:
    bad = pyjwt.encode(
        {"type": "access"},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(InvalidTokenError, match="missing or invalid sub"):
        decode_access_token(bad)


def test_decode_rejects_non_integer_sub() -> None:
    bad = pyjwt.encode(
        {"sub": "not-a-number", "type": "access"},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(InvalidTokenError, match="missing or invalid sub"):
        decode_access_token(bad)
