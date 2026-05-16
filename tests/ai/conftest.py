"""Shared fixtures and helpers for AI endpoint tests."""

import hashlib
import uuid
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from gigachat.models import ChatCompletion, Models
from redis.asyncio import ConnectionPool, Redis

from gritter.services.ai.dependencies import get_gigachat

FAKE_MODELS_PAYLOAD: dict[str, Any] = {
    "object": "list",
    "data": [
        {"id": "GigaChat", "object": "model", "owned_by": "salutedevices"},
        {"id": "GigaChat-2", "object": "model", "owned_by": "salutedevices"},
        {"id": "GigaChat-2-Max", "object": "model", "owned_by": "salutedevices"},
        {"id": "Embeddings", "object": "model", "owned_by": "salutedevices"},
    ],
}

FAKE_CHAT_CONTENT = "В Солнечной системе 8 планет."  # noqa: RUF001

FAKE_CHAT_PAYLOAD: dict[str, Any] = {
    "choices": [
        {
            "message": {
                "role": "assistant",
                "content": FAKE_CHAT_CONTENT,
                "function_call": None,
                "name": None,
                "attachments": None,
                "data_for_context": None,
                "functions_state_id": None,
                "reasoning_content": None,
                "id": None,
            },
            "index": 0,
            "finish_reason": "stop",
        },
    ],
    "created": 1778954372,
    "model": "GigaChat-2:2.0.28.2",
    "thread_id": None,
    "message_id": None,
    "usage": {
        "prompt_tokens": 26,
        "completion_tokens": 52,
        "total_tokens": 78,
        "precached_prompt_tokens": 2,
    },
    "object": "chat.completion",
}


def hashed_prompt(prompt: str) -> str:
    """Return SHA-256 hex digest used by `get_cached_gigachat` as the cache key."""
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


@pytest.fixture
def fake_models() -> Models:
    """A GigaChat `Models` response shaped like the real one."""
    return Models.model_validate(FAKE_MODELS_PAYLOAD)


@pytest.fixture
def fake_chat_completion() -> ChatCompletion:
    """A GigaChat `ChatCompletion` response shaped like the real one."""
    return ChatCompletion.model_validate(FAKE_CHAT_PAYLOAD)


@pytest.fixture
def gigachat_mock(fastapi_app: FastAPI) -> Mock:
    """A Mock GigaChat client wired in via `dependency_overrides`.

    Tests configure return values / side effects on the mock; no test ever
    talks to the real GigaChat service.
    """
    mock = Mock()
    fastapi_app.dependency_overrides[get_gigachat] = lambda: mock
    return mock


@pytest.fixture
async def unique_prompt(
    test_redis_pool: ConnectionPool,
) -> AsyncGenerator[str, None]:
    """A fresh prompt per test plus auto-cleanup of its Redis cache entry.

    `get_cached_gigachat` writes to Redis without a TTL, so without explicit
    cleanup these keys would leak across runs and break cache-miss tests.
    """
    prompt = f"test-prompt-{uuid.uuid4().hex}"
    yield prompt
    async with Redis(connection_pool=test_redis_pool) as redis:
        await redis.delete(hashed_prompt(prompt))
