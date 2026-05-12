"""Pydantic schemas for auth endpoints."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RegisterIn(BaseModel):
    """Body of `POST /auth/register`."""

    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    login: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    """Body of `POST /auth/login`."""

    login: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=1, max_length=128)


class RefreshIn(BaseModel):
    """Body of `POST /auth/refresh`."""

    refresh_token: str = Field(min_length=1)


class ChangePasswordIn(BaseModel):
    """Body of `POST /auth/change-password`."""

    old_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    """Public projection of a user (no password_hash)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    first_name: str
    last_name: str
    login: str
    avatar_url: str | None
    created_at: datetime


class TokenPair(BaseModel):
    """Access + refresh tokens."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105
