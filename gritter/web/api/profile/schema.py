"""Pydantic schemas for profile endpoints."""

from datetime import datetime

from pydantic import BaseModel


class FollowOut(BaseModel):
    """Confirmation of a `POST /users/{id}/follow`."""

    follower_id: int
    followee_id: int
    created_at: datetime


class FeedItem(BaseModel):
    """One post in the feed."""

    id: int
    user_id: int
    title: str
    content: str
    category: str | None
    created_at: datetime


class PaginatedFeed(BaseModel):
    """Paginated feed envelope."""

    items: list[FeedItem]
    total: int
    page: int
    size: int
    has_next: bool
