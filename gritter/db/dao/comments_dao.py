"""DAO for the ``comments`` table.

Each write that changes the visible-comment population on a post is paired
with an atomic ``UPDATE posts SET comments_count = comments_count ± 1`` in
the same transaction.  Reads filter out soft-deleted rows.
"""

from collections.abc import Sequence
from datetime import datetime

from fastapi import Depends
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from gritter.db.dependencies import get_db_session
from gritter.db.models.comments import Comment
from gritter.db.models.posts import Post


class CommentDAO:
    """Create / read / soft-delete comments with paired counter maintenance."""

    def __init__(self, session: AsyncSession = Depends(get_db_session)) -> None:
        self.session = session

    async def create(self, *, post_id: int, user_id: int, content: str) -> Comment:
        """Insert a comment and increment ``posts.comments_count`` atomically."""
        comment = Comment(post_id=post_id, user_id=user_id, content=content)
        self.session.add(comment)
        await self.session.execute(
            update(Post)
            .where(Post.id == post_id)
            .values(comments_count=Post.comments_count + 1)
        )
        await self.session.flush()
        await self.session.refresh(comment)
        return comment

    async def get_by_id(self, comment_id: int) -> Comment | None:
        """Return a non-deleted comment, or ``None``."""
        stmt = select(Comment).where(
            Comment.id == comment_id, Comment.deleted_at.is_(None)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def soft_delete(self, comment: Comment) -> None:
        """Mark the comment as soft-deleted and decrement the post counter.

        Caller is responsible for authorisation; this method does not
        verify ownership.
        """
        comment.deleted_at = datetime.now(tz=None)
        await self.session.execute(
            update(Post)
            .where(Post.id == comment.post_id)
            .values(comments_count=Post.comments_count - 1)
        )
        await self.session.flush()

    async def count_for_post(self, post_id: int) -> int:
        """Number of visible (non-deleted) comments on ``post_id``."""
        stmt = (
            select(func.count())
            .select_from(Comment)
            .where(Comment.post_id == post_id, Comment.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def list_for_post(
        self, post_id: int, *, offset: int, limit: int
    ) -> Sequence[Comment]:
        """Paginated, oldest-first comments on ``post_id`` (US-3.3)."""
        stmt = (
            select(Comment)
            .where(Comment.post_id == post_id, Comment.deleted_at.is_(None))
            .order_by(Comment.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
