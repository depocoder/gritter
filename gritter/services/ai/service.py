"""Servise for getting data from redis."""

import hashlib

from fastapi import Depends
from gigachat import ChatCompletion, GigaChat
from redis.asyncio import ConnectionPool, Redis

from gritter.services.ai.dependencies import get_gigachat
from gritter.services.redis.dependency import get_redis_pool
from gritter.web.api.ai.schema import InstanceAI


async def get_cached_gigachat(
    data: InstanceAI,
    gigachat: GigaChat = Depends(get_gigachat),
    redis_pool: ConnectionPool = Depends(get_redis_pool),
) -> ChatCompletion:
    """
    Gets cached gigachat.

    :param data: Instance AI.
    :param gigachat: GigaChat AI.
    :param redis_pool: redis connection pool.
    :returns: ChatCompletion.
    """
    prompt = data.prompt
    hashed_prompt = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    async with Redis(connection_pool=redis_pool) as redis:
        cached_response = await redis.get(hashed_prompt)
        if cached_response:
            return ChatCompletion.model_validate_json(cached_response)

        gigachat_response = gigachat.chat(data.prompt)
        cached_response = gigachat_response.model_dump_json(by_alias=True)
        await redis.set(name=hashed_prompt, value=cached_response)
        return gigachat_response
