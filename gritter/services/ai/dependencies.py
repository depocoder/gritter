from gigachat import GigaChat

from gritter.settings import settings


def get_gigachat() -> GigaChat:
    """
    Get gigachat from the state.

    :return: gigachat.
    """
    return GigaChat(
        credentials=settings.gigachat_authorization_key, verify_ssl_certs=False
    )
