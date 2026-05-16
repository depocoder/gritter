"""Pydantic schemas for likes endpoints."""

from pydantic import BaseModel


class LikeStateOut(BaseModel):
    """Body of ``POST /api/posts/{id}/like`` 200 response.

    ``liked`` is always ``True`` for POST (the operation expresses an intent,
    not a diff); ``likes_count`` is the post-state counter so the client can
    update its UI without an extra GET.
    """

    liked: bool
    likes_count: int
