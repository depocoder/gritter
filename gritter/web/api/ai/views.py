from fastapi import APIRouter, Depends
from gigachat import ChatCompletion, GigaChat, Models
from redis.asyncio import ConnectionPool

from gritter.services.ai.dependencies import get_gigachat
from gritter.services.ai.service import get_cached_gigachat
from gritter.services.redis.dependency import get_redis_pool
from gritter.web.api.ai.schema import InstanceAI

router = APIRouter()


@router.post("/chat")
async def chat(
    data: InstanceAI,
    gigachat: GigaChat = Depends(get_gigachat),
    redis_pool: ConnectionPool = Depends(get_redis_pool),
) -> ChatCompletion:
    """
    Sends post to GigaChat.

    :param data: Instance AI.
    :param gigachat: GigaChat AI.
    :param redis_pool: redis connection pool.
    :returns: ChatCompletion.
    """
    return await get_cached_gigachat(data, gigachat, redis_pool)


@router.get("/models")
async def get_gigachat_model(
    gigachat: GigaChat = Depends(get_gigachat),
) -> Models:
    """
    Returns GigaChat models.

    :param get_gigachat: GigaChat

    """
    return gigachat.get_models()
