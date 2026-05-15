from fastapi import APIRouter, Depends

from gritter.services.ai.dependencies import get_gigachat
from gritter.web.api.ai.schema import InstanceAI

router = APIRouter()


@router.post("/chat")
async def send_post(
    data: InstanceAI,
    gigachat: get_gigachat = Depends(get_gigachat)
) -> None:
    """
    Sends post to GigaChat.

    :param data: .
    :returns: .
    """
    return gigachat.embeddings([data])


@router.get("/models")
async def get_gigachat_model(
    gigachat: get_gigachat = Depends(get_gigachat),
) -> None:
    """
    Returns GigaChat models.

    :param get_gigachat: GigaChat

    """
    return gigachat.get_models()
