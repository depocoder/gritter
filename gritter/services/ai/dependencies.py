from typing import Annotated

from fastapi import Header
from gigachat import GigaChat

from gritter.settings import settings


def get_gigachat(
    model: Annotated[str | None, Header()] = settings.gigachat_standard_model,
) -> GigaChat:
    """
    Get gigachat from the state.

    :return: gigachat.
    """
    return GigaChat(
        credentials=settings.gigachat_authorization_key,
        verify_ssl_certs=False,
        model=model,
    )
