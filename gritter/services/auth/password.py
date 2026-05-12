"""Argon2id password hashing."""

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_hasher = PasswordHasher()


def hash_password(plain: str) -> str:
    """Hash a plaintext password with argon2id."""
    return _hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if `plain` matches the stored `hashed` digest."""
    try:
        return _hasher.verify(hashed, plain)
    except VerifyMismatchError:
        return False
