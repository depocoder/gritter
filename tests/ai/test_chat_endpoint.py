"""Tests for the cached AI chat endpoint (`POST /api/ai/chat`)."""

from unittest.mock import Mock

from gigachat.models import ChatCompletion
from httpx import AsyncClient
from redis.asyncio import ConnectionPool, Redis
from starlette import status

from tests.ai.conftest import FAKE_CHAT_CONTENT, hashed_prompt


async def test_chat_cache_miss_calls_gigachat_and_caches(
    client: AsyncClient,
    test_redis_pool: ConnectionPool,
    gigachat_mock: Mock,
    fake_chat_completion: ChatCompletion,
    unique_prompt: str,
) -> None:
    """On a cache miss: call GigaChat once, store JSON in Redis, return it."""

    gigachat_mock.chat.return_value = fake_chat_completion

    response = await client.post(
        "/api/ai/chat",
        json={"prompt": unique_prompt},
        headers={"model": "GigaChat-2"},
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["object"] == "chat.completion"
    assert body["choices"][0]["message"]["content"] == FAKE_CHAT_CONTENT
    gigachat_mock.chat.assert_called_once_with(unique_prompt)

    async with Redis(connection_pool=test_redis_pool) as redis:
        cached_raw = await redis.get(hashed_prompt(unique_prompt))
    assert cached_raw is not None
    cached = ChatCompletion.model_validate_json(cached_raw)
    assert cached.choices[0].message.content == FAKE_CHAT_CONTENT


async def test_chat_cache_hit_skips_gigachat(
    client: AsyncClient,
    test_redis_pool: ConnectionPool,
    gigachat_mock: Mock,
    fake_chat_completion: ChatCompletion,
    unique_prompt: str,
) -> None:
    """On a cache hit: serve from Redis without calling GigaChat."""

    async with Redis(connection_pool=test_redis_pool) as redis:
        await redis.set(
            hashed_prompt(unique_prompt),
            fake_chat_completion.model_dump_json(by_alias=True),
        )
    gigachat_mock.chat.side_effect = AssertionError(
        "gigachat.chat must not be called on cache hit"
    )

    response = await client.post(
        "/api/ai/chat",
        json={"prompt": unique_prompt},
        headers={"model": "GigaChat-2"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["choices"][0]["message"]["content"] == FAKE_CHAT_CONTENT
    gigachat_mock.chat.assert_not_called()


async def test_chat_empty_prompt_returns_422(
    client: AsyncClient,
    gigachat_mock: Mock,  # overrides dep so no real GigaChat is hit
) -> None:
    """`InstanceAI.prompt` has `min_length=1` — empty input is rejected."""

    response = await client.post(
        "/api/ai/chat",
        json={"prompt": ""},
        headers={"model": "GigaChat-2"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
