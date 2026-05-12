from redis.asyncio import ConnectionPool, Redis

from gritter.services.auth.refresh import (
    _hash_token,
    _key,
    consume_refresh_token,
    issue_refresh_token,
)


async def test_issue_then_consume_returns_user_id(
    test_redis_pool: ConnectionPool,
) -> None:
    async with Redis(connection_pool=test_redis_pool) as redis:
        token = await issue_refresh_token(redis, user_id=7)
        assert await consume_refresh_token(redis, token) == 7


async def test_consume_is_single_use(test_redis_pool: ConnectionPool) -> None:
    async with Redis(connection_pool=test_redis_pool) as redis:
        token = await issue_refresh_token(redis, user_id=11)
        assert await consume_refresh_token(redis, token) == 11
        assert await consume_refresh_token(redis, token) is None


async def test_consume_unknown_token_returns_none(
    test_redis_pool: ConnectionPool,
) -> None:
    async with Redis(connection_pool=test_redis_pool) as redis:
        assert await consume_refresh_token(redis, "nonexistent") is None


async def test_consume_corrupt_value_returns_none(
    test_redis_pool: ConnectionPool,
) -> None:
    """If something stored a non-numeric value under the key, treat as invalid."""
    fake_token = "corrupted-token"
    async with Redis(connection_pool=test_redis_pool) as redis:
        await redis.set(_key(fake_token), "not-an-int")
        try:
            assert await consume_refresh_token(redis, fake_token) is None
        finally:
            await redis.delete(_key(fake_token))


async def test_consume_handles_str_values() -> None:
    """If the pool is configured with decode_responses=True, GET returns str."""
    from gritter.settings import settings

    pool = ConnectionPool.from_url(str(settings.redis_url), decode_responses=True)
    try:
        async with Redis(connection_pool=pool) as redis:
            token = await issue_refresh_token(redis, user_id=99)
            assert await consume_refresh_token(redis, token) == 99
    finally:
        await pool.disconnect()


def test_hash_token_is_deterministic() -> None:
    assert _hash_token("abc") == _hash_token("abc")
    assert _hash_token("abc") != _hash_token("abd")
