"""DAO for the `follows` table."""

from collections.abc import Sequence

from fastapi import Depends
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from gritter.db.dependencies import get_db_session
from gritter.db.models.follows import Follow


class FollowDAO:
    """Read/write access to follow edges."""

    def __init__(self, session: AsyncSession = Depends(get_db_session)) -> None:
        self.session = session

    async def exists(self, follower_id: int, followee_id: int) -> bool:
        """Return True iff `follower_id` already follows `followee_id`."""
        stmt = select(Follow).where(
            Follow.follower_id == follower_id,
            Follow.followee_id == followee_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def create(self, follower_id: int, followee_id: int) -> Follow:
        """Insert a follow edge (caller pre-checks for duplicates)."""
        follow = Follow(follower_id=follower_id, followee_id=followee_id)
        self.session.add(follow)
        await self.session.flush()
        await self.session.refresh(follow)
        return follow

    async def delete(self, follower_id: int, followee_id: int) -> int:
        """Delete a follow edge; returns rowcount (0 or 1)."""
        stmt = delete(Follow).where(
            Follow.follower_id == follower_id,
            Follow.followee_id == followee_id,
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        rowcount: int = result.rowcount  # type: ignore[attr-defined]
        return rowcount or 0

    async def list_followee_ids(self, follower_id: int) -> Sequence[int]:
        """Return ids of users that `follower_id` follows."""
        stmt = select(Follow.followee_id).where(Follow.follower_id == follower_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()
