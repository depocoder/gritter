"""DAO for the ``likes`` table.

Encapsulates the toggle-with-counter pattern: every successful insert/delete
of a like is paired with an atomic increment/decrement of
``posts.likes_count`` inside the same transaction.  Both statements share the
session injected by :func:`gritter.db.dependencies.get_db_session`, so commit
and rollback are handled at request scope.
"""

from fastapi import Depends
from sqlalchemy import delete, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from gritter.db.dependencies import get_db_session
from gritter.db.models.likes import Like
from gritter.db.models.posts import Post


class LikeDAO:
    """Idempotent add/remove of a like + paired counter update."""

    def __init__(self, session: AsyncSession = Depends(get_db_session)) -> None:
        self.session = session

    async def add(self, *, post_id: int, user_id: int) -> bool:
        """Insert a like idempotently; return ``True`` iff a new row appeared.

        Uses ``INSERT ... ON CONFLICT DO NOTHING RETURNING post_id`` on the
        composite PK ``(post_id, user_id)``.  The ``RETURNING`` clause yields a
        row only when an insert actually happened — a duplicate POST gets
        ``None`` back, which is how we know to skip the counter increment.
        Relying on ``RETURNING`` instead of ``rowcount`` keeps the contract
        independent of driver-specific quirks.

        The paired ``UPDATE posts SET likes_count = likes_count + 1`` is
        SQL-side arithmetic — Postgres takes a row-lock during the update, so
        we are safe from lost updates under concurrency.
        """
        stmt = (
            pg_insert(Like)
            .values(post_id=post_id, user_id=user_id)
            .on_conflict_do_nothing(index_elements=["post_id", "user_id"])
            .returning(Like.post_id)
        )
        result = await self.session.execute(stmt)
        if result.scalar_one_or_none() is None:
            return False
        await self.session.execute(
            update(Post)
            .where(Post.id == post_id)
            .values(likes_count=Post.likes_count + 1)
        )
        await self.session.flush()
        return True

    async def remove(self, *, post_id: int, user_id: int) -> bool:
        """Delete a like; return ``True`` iff a row was actually removed.

        ``DELETE ... RETURNING post_id`` returns the deleted row's key when
        a row existed, and yields nothing otherwise.  Only on a real removal
        do we decrement the counter.  The ``CHECK (likes_count >= 0)``
        constraint on ``posts`` guards against a double-decrement bug ever
        shipping silently.
        """
        result = await self.session.execute(
            delete(Like)
            .where(Like.post_id == post_id, Like.user_id == user_id)
            .returning(Like.post_id)
        )
        if result.scalar_one_or_none() is None:
            return False
        await self.session.execute(
            update(Post)
            .where(Post.id == post_id)
            .values(likes_count=Post.likes_count - 1)
        )
        await self.session.flush()
        return True
