"""Likes (Эпик 3) endpoints: toggle a like on a post."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response

from gritter.db.dao.likes_dao import LikeDAO
from gritter.db.dao.posts_dao import PostDAO
from gritter.db.models.posts import Post, PostStatus
from gritter.db.models.users import User
from gritter.web.api.auth.dependencies import get_current_user
from gritter.web.api.likes.schema import LikeStateOut

router = APIRouter()


async def _get_visible_post(
    post_dao: PostDAO, post_id: int, current_user: User
) -> Post:
    """Return the post if the current user is allowed to see it, else 404.

    Mirrors the visibility rule used in ``posts/views.py``: published posts
    are public; on-moderation posts are visible only to their author.  We
    return 404 (not 403) so the existence of a draft is not leaked.
    """
    post = await post_dao.get_by_id(post_id)
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found."
        )
    if post.status != PostStatus.published and post.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found."
        )
    return post


@router.post("/posts/{post_id}/like", response_model=LikeStateOut, name="like_post")
async def like_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    post_dao: PostDAO = Depends(),
    like_dao: LikeDAO = Depends(),
) -> LikeStateOut:
    """Idempotent toggle-on of a like (US-3.1).

    A repeated POST is a no-op at the DB level (``ON CONFLICT DO NOTHING``)
    and the response is the post-state, not a diff — ``liked`` is always
    ``True`` and ``likes_count`` reflects the latest counter value.
    """
    post = await _get_visible_post(post_dao, post_id, current_user)
    # Snapshot the counter BEFORE LikeDAO.add: SQLAlchemy 2.x's default
    # ``synchronize_session='auto'`` mutates ``post.likes_count`` in place when
    # the DAO runs its ``UPDATE posts SET likes_count = likes_count + 1``.
    # Reading ``post.likes_count`` after the call would already reflect the
    # increment, so adding 1 on top would double-count.
    likes_before = post.likes_count
    inserted = await like_dao.add(post_id=post.id, user_id=current_user.id)
    return LikeStateOut(
        liked=True,
        likes_count=likes_before + (1 if inserted else 0),
    )


@router.delete(
    "/posts/{post_id}/like",
    status_code=status.HTTP_204_NO_CONTENT,
    name="unlike_post",
)
async def unlike_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    post_dao: PostDAO = Depends(),
    like_dao: LikeDAO = Depends(),
) -> Response:
    """Idempotent toggle-off of a like (US-3.1).

    Returns 204 whether or not the user had previously liked the post —
    repeated DELETE is intentionally not a 404.
    """
    post = await _get_visible_post(post_dao, post_id, current_user)
    await like_dao.remove(post_id=post.id, user_id=current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
