"""DAO for the `posts` table (feed reads only — Эпик 5 scope)."""

from collections.abc import Sequence

from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from gritter.db.dependencies import get_db_session
from gritter.db.models.posts import Post, PostStatus


class PostDAO:
    """Feed-oriented reads for `posts`."""

    def __init__(self, session: AsyncSession = Depends(get_db_session)) -> None:
        self.session = session

    async def count_feed(self, author_ids: Sequence[int]) -> int:
        """Count published, non-deleted posts authored by `author_ids`."""
        if not author_ids:
            return 0
        stmt = (
            select(func.count())
            .select_from(Post)
            .where(
                Post.user_id.in_(author_ids),
                Post.status == PostStatus.published,
                Post.deleted_at.is_(None),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def list_feed(
        self,
        author_ids: Sequence[int],
        *,
        offset: int,
        limit: int,
    ) -> Sequence[Post]:
        """Fetch a page of feed posts ordered by `created_at DESC`."""
        if not author_ids:
            return []
        stmt = (
            select(Post)
            .where(
                Post.user_id.in_(author_ids),
                Post.status == PostStatus.published,
                Post.deleted_at.is_(None),
            )
            .order_by(Post.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
