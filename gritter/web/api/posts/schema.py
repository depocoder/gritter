"""Pydantic schemas for posts endpoints."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from gritter.db.models.posts import (
    POST_CATEGORY_MAX_LEN,
    POST_CONTENT_MAX_LEN,
    POST_TITLE_MAX_LEN,
    AgeRating,
    PostStatus,
    Sentiment,
)

MODERATION_MESSAGE = "Пост отправлен на проверку"


class PostCreateIn(BaseModel):
    """Body of `POST /api/posts`."""

    title: str = Field(min_length=1, max_length=POST_TITLE_MAX_LEN)
    content: str = Field(min_length=1, max_length=POST_CONTENT_MAX_LEN)
    category: str | None = Field(default=None, max_length=POST_CATEGORY_MAX_LEN)


class PostUpdateIn(BaseModel):
    """Body of `PATCH /api/posts/{id}` (all fields optional)."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=POST_TITLE_MAX_LEN)
    content: str | None = Field(
        default=None, min_length=1, max_length=POST_CONTENT_MAX_LEN
    )
    category: str | None = Field(default=None, max_length=POST_CATEGORY_MAX_LEN)


class AuthorOut(BaseModel):
    """Public author projection embedded in post responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    login: str
    first_name: str
    last_name: str
    avatar_url: str | None


class PostOut(BaseModel):
    """Full post view returned to readers."""

    id: int
    title: str
    content: str
    category: str | None
    status: PostStatus
    sentiment: Sentiment | None
    age_rating: AgeRating | None
    likes_count: int
    comments_count: int
    created_at: datetime
    updated_at: datetime
    author: AuthorOut


class MyPostOut(PostOut):
    """Author-facing post view (extra `is_on_moderation` flag, US-2.6)."""

    is_on_moderation: bool


class PostCreatedOut(BaseModel):
    """Body of `POST /api/posts` 201 response."""

    id: int
    status: PostStatus
    moderation_message: str = MODERATION_MESSAGE


class PaginatedPosts(BaseModel):
    """Paginated public-feed envelope."""

    items: list[PostOut]
    total: int
    page: int
    size: int
    has_next: bool


class PaginatedMyPosts(BaseModel):
    """Paginated author-feed envelope."""

    items: list[MyPostOut]
    total: int
    page: int
    size: int
    has_next: bool
