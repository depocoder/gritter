"""DAO for the `posts` table."""

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import TypeVar

from fastapi import Depends
from sqlalchemy import ColumnElement, Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from gritter.db.dependencies import get_db_session
from gritter.db.models.posts import AgeRating, Post, PostStatus, Sentiment

_S = TypeVar("_S", bound=Select)  # type: ignore[type-arg]


class PostDAO:
    """Read/write access to posts."""

    def __init__(self, session: AsyncSession = Depends(get_db_session)) -> None:
        self.session = session

    async def create(
        self,
        *,
        user_id: int,
        title: str,
        content: str,
        category: str | None,
    ) -> Post:
        """Insert a new on-moderation post; returns the persisted entity."""
        post = Post(
            user_id=user_id,
            title=title,
            content=content,
            category=category,
            status=PostStatus.on_moderation,
        )
        self.session.add(post)
        await self.session.flush()
        await self.session.refresh(post)
        return post

    async def get_by_id(self, post_id: int) -> Post | None:
        """Return a post (any status) excluding soft-deleted, or None."""
        stmt = select(Post).where(Post.id == post_id, Post.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def soft_delete(self, post: Post) -> None:
        """Mark a post as soft-deleted (caller verifies authorship)."""
        post.deleted_at = datetime.now(tz=None)
        await self.session.flush()

    async def reset_for_remoderation(
        self,
        post: Post,
        *,
        title: str | None = None,
        content: str | None = None,
        category: str | None = None,
    ) -> None:
        """Apply edits and reset moderation state if title/content changed."""
        content_changed = (title is not None and title != post.title) or (
            content is not None and content != post.content
        )
        if title is not None:
            post.title = title
        if content is not None:
            post.content = content
        if category is not None:
            post.category = category
        if content_changed:
            post.status = PostStatus.on_moderation
            post.sentiment = None
            post.age_rating = None
            post.moderated_at = None
        await self.session.flush()
        await self.session.refresh(post)

    async def set_moderation_result(
        self,
        post: Post,
        *,
        sentiment: Sentiment,
        age_rating: AgeRating,
    ) -> None:
        """DS lkfgldkfgdlfkg ."""
        post.sentiment = sentiment
        post.age_rating = age_rating
        post.status = PostStatus.published
        post.moderated_at = datetime.now(tz=UTC).replace(tzinfo=None)
        post.moderation_attempts += 1
        await self.session.flush()

    async def bump_moderation_attempt(self, post: Post) -> None:
        """RFd fdf."""
        post.moderation_attempts += 1
        await self.session.flush()

    @staticmethod
    def _public_filter() -> tuple[ColumnElement[bool], ...]:
        return (
            Post.status == PostStatus.published,
            Post.deleted_at.is_(None),
        )

    @staticmethod
    def _apply_filters(
        stmt: _S,
        *,
        author_id: int | None,
        category: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> _S:
        if author_id is not None:
            stmt = stmt.where(Post.user_id == author_id)
        if category is not None:
            stmt = stmt.where(Post.category == category)
        if date_from is not None:
            stmt = stmt.where(Post.created_at >= date_from)
        if date_to is not None:
            stmt = stmt.where(Post.created_at <= date_to)
        return stmt

    async def count_published(
        self,
        *,
        author_id: int | None = None,
        category: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> int:
        """Count published, non-deleted posts matching the optional filters."""
        stmt = select(func.count()).select_from(Post).where(*self._public_filter())
        stmt = self._apply_filters(
            stmt,
            author_id=author_id,
            category=category,
            date_from=date_from,
            date_to=date_to,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def list_published(
        self,
        *,
        offset: int,
        limit: int,
        author_id: int | None = None,
        category: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> Sequence[Post]:
        """Page through the public feed (newest first)."""
        stmt = select(Post).where(*self._public_filter())
        stmt = self._apply_filters(
            stmt,
            author_id=author_id,
            category=category,
            date_from=date_from,
            date_to=date_to,
        )
        stmt = stmt.order_by(Post.created_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_by_author(
        self, author_id: int, *, status: PostStatus | None = None
    ) -> int:
        """Count an author's non-deleted posts (optional status filter)."""
        stmt = (
            select(func.count())
            .select_from(Post)
            .where(Post.user_id == author_id, Post.deleted_at.is_(None))
        )
        if status is not None:
            stmt = stmt.where(Post.status == status)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def list_by_author(
        self,
        author_id: int,
        *,
        offset: int,
        limit: int,
        status: PostStatus | None = None,
    ) -> Sequence[Post]:
        """Page through an author's non-deleted posts (newest first)."""
        stmt = (
            select(Post)
            .where(Post.user_id == author_id, Post.deleted_at.is_(None))
            .order_by(Post.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        if status is not None:
            stmt = stmt.where(Post.status == status)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_feed(self, author_ids: Sequence[int]) -> int:
        """Count published, non-deleted posts authored by `author_ids`."""
        if not author_ids:
            return 0
        stmt = (
            select(func.count())
            .select_from(Post)
            .where(Post.user_id.in_(author_ids), *self._public_filter())
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
            .where(Post.user_id.in_(author_ids), *self._public_filter())
            .order_by(Post.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
