"""Shared fixtures and helpers for moderation-worker tests."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import cast
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
import tenacity
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from gritter.db.dao.posts_dao import PostDAO
from gritter.db.models.posts import Post
from gritter.db.models.users import User
from gritter.services.worker.__main__ import _classify_with_gigachat


@pytest.fixture(autouse=True)
def _no_retry_wait(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace tenacity's jittered backoff with a no-op so retries don't sleep.

    Without this, every `_classify_with_gigachat` failure-path test would
    sit idle for up to 30 seconds while tenacity slept between retries.
    """
    monkeypatch.setattr(
        _classify_with_gigachat.retry,  # type: ignore[attr-defined]
        "wait",
        tenacity.wait_none(),
    )


@pytest.fixture
def session_factory(
    dbsession: AsyncSession,
) -> async_sessionmaker[AsyncSession]:
    """Wrap the per-test session so `handle_message` can `async with factory()`.

    The worker is typed against `async_sessionmaker[AsyncSession]`, but it only
    relies on the *protocol* `factory()` → async context manager → session.
    Our `@asynccontextmanager` wrapper satisfies that protocol at runtime, so
    we `cast` it to the expected type to keep mypy happy without changing
    production code.

    `session.commit()` inside the handler finalises an inner block; the outer
    transaction held by `dbsession` rolls back everything at test teardown.
    """

    @asynccontextmanager
    async def _factory() -> AsyncIterator[AsyncSession]:
        yield dbsession

    return cast("async_sessionmaker[AsyncSession]", _factory)


def make_message(
    body: bytes | str,
    *,
    routing_key: str = "post.created",
) -> MagicMock:
    """Build a Mock that behaves like `AbstractIncomingMessage`.

    Crucially, `message.process()` returns an async context manager that does
    NOT swallow exceptions — `__aexit__` returns `False`. Without this,
    a `raise` inside the handler (the ValidationError → DLQ path) would be
    silently eaten by an AsyncMock's default truthy return.
    """
    msg = MagicMock()
    msg.body = body if isinstance(body, bytes) else body.encode("utf-8")
    msg.routing_key = routing_key

    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=ctx)
    ctx.__aexit__ = AsyncMock(return_value=False)
    msg.process = MagicMock(return_value=ctx)

    return msg


def gigachat_returning(content: str) -> Mock:
    """Build a GigaChat mock whose `.chat(prompt)` yields `content` as text."""
    mock = Mock()
    response = Mock()
    response.choices = [Mock(message=Mock(content=content))]
    mock.chat.return_value = response
    return mock


async def make_user_and_post(
    session: AsyncSession,
    login: str,
    *,
    title: str = "t",
    content: str = "c",
) -> tuple[User, Post]:
    """Insert a user + a fresh on-moderation post; return both."""
    user = User(first_name="A", last_name="B", login=login, password_hash="x")
    session.add(user)
    await session.flush()
    dao = PostDAO(session)
    post = await dao.create(
        user_id=user.id, title=title, content=content, category=None
    )
    return user, post
