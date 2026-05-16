"""Pydantic schemas for comments endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field

from gritter.db.models.comments import COMMENT_CONTENT_MAX_LEN
from gritter.web.api.posts.schema import AuthorOut


class CommentCreateIn(BaseModel):
    """Body of ``POST /api/posts/{id}/comments``."""

    content: str = Field(min_length=1, max_length=COMMENT_CONTENT_MAX_LEN)


class CommentOut(BaseModel):
    """Public comment view used in single-create and listing responses."""

    id: int
    post_id: int
    content: str
    created_at: datetime
    author: AuthorOut


class PaginatedComments(BaseModel):
    """Paginated envelope mirroring the posts feed shape (US-3.3)."""

    items: list[CommentOut]
    total: int
    page: int
    size: int
    has_next: bool
