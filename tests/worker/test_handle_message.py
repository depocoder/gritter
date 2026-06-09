"""Tests for `handle_message` (Эпик 4: US-4.1, US-6.3, US-7.1)."""

import json
from unittest.mock import Mock

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from gritter.db.models.posts import AgeRating, PostStatus, Sentiment
from gritter.services.worker.__main__ import make_handle_message
from tests.worker.conftest import (
    gigachat_returning,
    make_message,
    make_user_and_post,
)

_SessionFactory = async_sessionmaker[AsyncSession]


async def test_handle_bad_payload_goes_to_dlq(
    session_factory: _SessionFactory,
) -> None:
    """Non-JSON body → `message.process(requeue=False)` (US-7.1)."""

    gigachat = Mock()
    handler = make_handle_message(session_factory, gigachat)
    msg = make_message(b"not a json")

    await handler(msg)

    msg.process.assert_called_once_with(requeue=False)
    gigachat.chat.assert_not_called()


async def test_handle_payload_without_post_id_goes_to_dlq(
    session_factory: _SessionFactory,
) -> None:
    """Missing `post_id` key → DLQ (KeyError caught with the other parse errors)."""

    gigachat = Mock()
    handler = make_handle_message(session_factory, gigachat)
    msg = make_message(json.dumps({"event_type": "post.created"}))

    await handler(msg)

    msg.process.assert_called_once_with(requeue=False)
    gigachat.chat.assert_not_called()


async def test_handle_post_not_found_skips(
    session_factory: _SessionFactory,
) -> None:
    """Unknown post_id → ack without calling GigaChat."""

    gigachat = Mock()
    handler = make_handle_message(session_factory, gigachat)
    msg = make_message(json.dumps({"post_id": 99999}))

    await handler(msg)

    gigachat.chat.assert_not_called()


async def test_handle_already_moderated_skips(
    session_factory: _SessionFactory,
    dbsession: AsyncSession,
) -> None:
    """Idempotency (US-6.3): re-delivered events for published posts are no-ops."""

    _, post = await make_user_and_post(dbsession, "handle-skip")
    post.status = PostStatus.published
    await dbsession.flush()
    gigachat = Mock()
    handler = make_handle_message(session_factory, gigachat)
    msg = make_message(json.dumps({"post_id": post.id}))

    await handler(msg)

    gigachat.chat.assert_not_called()
    assert post.moderation_attempts == 0


async def test_handle_happy_path_updates_post(
    session_factory: _SessionFactory,
    dbsession: AsyncSession,
) -> None:
    """End-to-end happy path: GigaChat verdict applied, post published."""

    _, post = await make_user_and_post(dbsession, "handle-happy")
    gigachat = gigachat_returning('{"sentiment": "positive", "age_rating": "0+"}')
    handler = make_handle_message(session_factory, gigachat)
    msg = make_message(json.dumps({"post_id": post.id}))

    await handler(msg)

    await dbsession.refresh(post)
    assert post.status == PostStatus.published
    assert post.sentiment == Sentiment.positive
    assert post.age_rating == AgeRating.AGE_0
    assert post.moderation_attempts == 1
    assert post.moderated_at is not None


async def test_handle_gigachat_failure_bumps_attempt(
    session_factory: _SessionFactory,
    dbsession: AsyncSession,
) -> None:
    """Transient GigaChat error → attempts += 1, status untouched, no DLQ."""

    _, post = await make_user_and_post(dbsession, "handle-fail")
    gigachat = Mock()
    gigachat.chat.side_effect = Exception("upstream-timeout")
    handler = make_handle_message(session_factory, gigachat)
    msg = make_message(json.dumps({"post_id": post.id}))

    await handler(msg)

    await dbsession.refresh(post)
    assert post.status == PostStatus.on_moderation
    assert post.sentiment is None
    assert post.moderation_attempts == 1
    assert gigachat.chat.call_count == 3  # all tenacity retries exhausted


async def test_handle_validation_error_raises_for_dlq(
    session_factory: _SessionFactory,
    dbsession: AsyncSession,
) -> None:
    """Structural GigaChat error → bump attempts, then raise so RMQ routes to DLQ."""

    _, post = await make_user_and_post(dbsession, "handle-validation")
    gigachat = gigachat_returning('{"sentiment": "very_happy", "age_rating": "0+"}')
    handler = make_handle_message(session_factory, gigachat)
    msg = make_message(json.dumps({"post_id": post.id}))

    with pytest.raises(ValidationError):
        await handler(msg)

    await dbsession.refresh(post)
    assert post.moderation_attempts == 1
    assert post.status == PostStatus.on_moderation
    assert post.sentiment is None
