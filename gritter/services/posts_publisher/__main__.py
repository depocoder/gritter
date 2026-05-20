"""Entry-point for the posts-outbox publisher worker.

Polls `posts_outbox` for `pending` rows, publishes each one to RabbitMQ,
marks the row as `sent` on success or increments `attempts` / records
`last_error` on failure. Lives outside the FastAPI process so the API never
blocks on broker availability.

Run:
    uv run python -m gritter.services.posts_publisher
"""

import asyncio
import json

import aio_pika
from aio_pika.abc import AbstractRobustConnection
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from gritter.db.dao.posts_outbox_dao import PostsOutboxDAO
from gritter.settings import settings

POSTS_EXCHANGE = settings.posts_exchange
POLL_IDLE_SLEEP_SECONDS = settings.roll_idle_sleep_seconds
batch_size = settings.batch_size


async def _publish_one(
    exchange: aio_pika.abc.AbstractExchange,
    routing_key: str,
    body: bytes,
) -> None:
    """Publish to the `posts` topic exchange with a per-event routing key."""
    message = aio_pika.Message(
        body=body,
        content_type="application/json",
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
    )
    await exchange.publish(message, routing_key=routing_key)


async def _process_batch(
    session: AsyncSession,
    exchange: aio_pika.abc.AbstractExchange,
) -> int:
    """Drain one batch of pending rows. Returns how many were handled.

    The whole batch runs in one transaction so the `FOR UPDATE SKIP LOCKED`
    lock held in step 2 is released only after we commit the status update
    in step 4. That keeps two publisher instances safe to run side-by-side.
    """
    dao = PostsOutboxDAO(session=session)

    posts = await dao.get_posts(batch_size)

    if not posts:
        return 0

    for post in posts:
        try:
            body = json.dumps(post.payload).encode("utf-8")
            await _publish_one(exchange, post.event_type, body)
            await dao.mark_sent(post)
        except Exception as exc:
            logger.warning("Failed to publish outbox row {}: {}", post.id, exc)
            await dao.mark_failed(post, error=str(exc))

    await session.commit()
    return len(posts)


async def _run_forever(
    connection: AbstractRobustConnection,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Main poll loop: open a channel + session per iteration, sleep when idle."""
    async with connection.channel() as channel:
        exchange = await channel.declare_exchange(
            POSTS_EXCHANGE,
            aio_pika.ExchangeType.TOPIC,
            durable=True,
        )

        while True:
            async with session_factory() as session:
                try:
                    processed = await _process_batch(session, exchange)
                except Exception:
                    logger.exception("Outbox batch crashed; rolling back")
                    await session.rollback()
                    processed = 0

            if processed == 0:
                await asyncio.sleep(POLL_IDLE_SLEEP_SECONDS)


async def main() -> None:
    """Bring up DB + RMQ connections and hand off to the poll loop."""
    logger.info("Starting posts-outbox publisher")
    engine = create_async_engine(str(settings.db_url), echo=settings.db_echo)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    connection = await aio_pika.connect_robust(str(settings.rabbit_url))
    try:
        await _run_forever(connection, session_factory)
    finally:
        await connection.close()
        await engine.dispose()
        logger.info("Posts-outbox publisher stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
