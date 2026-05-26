import asyncio
import json
from collections.abc import Awaitable, Callable
from contextlib import suppress

import aio_pika
from aio_pika.abc import (
    AbstractChannel,
    AbstractIncomingMessage,
    AbstractQueue,
    AbstractRobustConnection,
)
from gigachat import GigaChat
from loguru import logger
from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
)

from gritter.db.dao.posts_dao import PostDAO
from gritter.db.models import posts, users  # noqa: F401 # register ORM models
from gritter.db.models.posts import AgeRating, PostStatus, Sentiment
from gritter.settings import settings

POSTS_EXCHANGE = settings.posts_exchange
DLX_EXCHANGE = "posts.dlx"
CLASSIFICATION_QUEUE = "post_classification"
CLASSIFICATION_DLQ = "post_classification.dlq"
ROUTING_KEY_PATTERN = "post.*"


class ClassificationResult(BaseModel):
    """Strictly-typed wrapper for the JSON GigaChat returns."""

    sentiment: Sentiment
    age_rating: AgeRating


PROMPT_TEMPLATE = """Ты — модератор постов в социальной сети.
Проанализируй заголовок и текст и верни СТРОГО JSON без пояснений и без markdown-блоков.

Формат:
{{"sentiment": "<positive|neutral|negative>", "age_rating": "<0+|12+|16+|18+>"}}

Заголовок: {title}
Содержание: {content}
"""


@retry(
    stop=stop_after_attempt(3),
    wait=wait_random_exponential(min=1, max=10),
    reraise=True,
)
def _classify_with_gigachat(
    gigachat: GigaChat,
    *,
    title: str,
    content: str,
) -> ClassificationResult:
    """Call GigaChat and parse the response. Retried up to 3 times."""
    prompt = PROMPT_TEMPLATE.format(title=title, content=content)
    response = gigachat.chat(prompt)
    raw = response.choices[0].message.content
    data = json.loads(raw)
    return ClassificationResult.model_validate(data)


def make_handle_message(
    session_factory: async_sessionmaker[AsyncSession],
    gigachat: GigaChat,
) -> Callable[[AbstractIncomingMessage], Awaitable[None]]:
    """Build a handler that closes over the session factory and GigaChat client."""

    async def handle_message(message: AbstractIncomingMessage) -> None:
        try:
            payload = json.loads(message.body)
            post_id = int(payload["post_id"])
        except (json.JSONDecodeError, KeyError, ValueError, TypeError) as exc:
            logger.error(
                "Bad payload, sending to DLQ. body={!r}, error={}",
                message.body,
                exc,
            )
            async with message.process(requeue=False):
                pass  # nack(requeue=False) → DLQ
            return

        async with message.process(requeue=False), session_factory() as session:
            dao = PostDAO(session=session)
            post = await dao.get_by_id(post_id)

            if post is None:
                logger.warning("Post {} not found, skipping", post_id)
                return
            if post.status != PostStatus.on_moderation:
                logger.info(
                    "Post {} already moderated (status={}), skipping",
                    post_id,
                    post.status,
                )
                return

            try:
                result = _classify_with_gigachat(
                    gigachat,
                    title=post.title,
                    content=post.content,
                )
            except ValidationError as exc:
                logger.error(
                    "Invalid classification format for post {}: {}",
                    post_id,
                    exc,
                )
                await dao.bump_moderation_attempt(post)
                await session.commit()
                raise
            except Exception as exc:
                logger.error(
                    "GigaChat failed for post {} after retries: {}",
                    post_id,
                    exc,
                )
                await dao.bump_moderation_attempt(post)
                await session.commit()
                return

            await dao.set_moderation_result(
                post,
                sentiment=result.sentiment,
                age_rating=result.age_rating,
            )
            await session.commit()
            logger.info(
                "Moderated post {}: sentiment={}, age_rating={}",
                post_id,
                result.sentiment,
                result.age_rating,
            )

    return handle_message


async def _setup_topology(channel: AbstractChannel) -> AbstractQueue:
    posts_exchange = await channel.declare_exchange(
        POSTS_EXCHANGE,
        aio_pika.ExchangeType.TOPIC,
        durable=True,
    )
    dlx_exchange = await channel.declare_exchange(
        DLX_EXCHANGE,
        aio_pika.ExchangeType.DIRECT,
        durable=True,
    )
    dlq = await channel.declare_queue(CLASSIFICATION_DLQ, durable=True)

    await dlq.bind(dlx_exchange, routing_key=CLASSIFICATION_DLQ)

    classification_queue = await channel.declare_queue(
        CLASSIFICATION_QUEUE,
        durable=True,
        arguments={
            "x-dead-letter-exchange": DLX_EXCHANGE,
            "x-dead-letter-routing-key": CLASSIFICATION_DLQ,
        },
    )

    await classification_queue.bind(posts_exchange, routing_key=ROUTING_KEY_PATTERN)

    return classification_queue


async def _run_forever(
    connection: AbstractRobustConnection,
    session_factory: async_sessionmaker[AsyncSession],
    gigachat: GigaChat,
) -> None:
    async with connection.channel() as channel:
        await channel.set_qos(prefetch_count=1)
        queue = await _setup_topology(channel)
        handler = make_handle_message(session_factory, gigachat)
        await queue.consume(handler)
        logger.info(
            "Worker is consuming queue {} (bound to {} via {})",
            CLASSIFICATION_QUEUE,
            POSTS_EXCHANGE,
            ROUTING_KEY_PATTERN,
        )
        await asyncio.Future()


async def main() -> None:
    """Main."""
    logger.info("Starting moderation worker")

    engine = create_async_engine(str(settings.db_url), echo=settings.db_echo)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    gigachat = GigaChat(
        credentials=settings.gigachat_authorization_key,
        verify_ssl_certs=False,
        model=settings.gigachat_standard_model,
    )
    connection = await aio_pika.connect_robust(str(settings.rabbit_url))
    try:
        await _run_forever(connection, session_factory, gigachat)
    finally:
        await connection.close()
        await engine.dispose()
        with suppress(Exception):
            gigachat.close()
        logger.info("Moderation worker stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
