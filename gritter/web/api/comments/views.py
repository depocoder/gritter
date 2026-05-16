"""Comments (Эпик 3) endpoints: create / list / soft-delete."""

from collections.abc import Sequence

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gritter.db.dao.comments_dao import CommentDAO
from gritter.db.dao.posts_dao import PostDAO
from gritter.db.dependencies import get_db_session
from gritter.db.models.comments import Comment
from gritter.db.models.posts import Post, PostStatus
from gritter.db.models.users import User
from gritter.web.api.auth.dependencies import (
    get_current_user,
    get_current_user_optional,
)
from gritter.web.api.comments.schema import (
    CommentCreateIn,
    CommentOut,
    PaginatedComments,
)
from gritter.web.api.posts.schema import AuthorOut

router = APIRouter()

DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 50


async def _get_visible_post(
    post_dao: PostDAO, post_id: int, current_user: User
) -> Post:
    """Return ``post_id`` if visible to ``current_user``, else raise 404.

    Mirrors the visibility rule used elsewhere: published posts are public;
    on-moderation posts are visible only to their author.  404 (not 403)
    so the existence of a draft is not leaked.
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


async def _load_comment_authors(
    session: AsyncSession, comments: Sequence[Comment]
) -> dict[int, User]:
    """Resolve authors for a page of comments in a single ``IN`` query."""
    if not comments:
        return {}
    user_ids = {c.user_id for c in comments}
    result = await session.execute(select(User).where(User.id.in_(user_ids)))
    return {u.id: u for u in result.scalars().all()}


def _to_comment_out(comment: Comment, author: User) -> CommentOut:
    return CommentOut(
        id=comment.id,
        post_id=comment.post_id,
        content=comment.content,
        created_at=comment.created_at,
        author=AuthorOut.model_validate(author),
    )


@router.post(
    "/posts/{post_id}/comments",
    response_model=CommentOut,
    status_code=status.HTTP_201_CREATED,
    name="create_comment",
)
async def create_comment(
    post_id: int,
    body: CommentCreateIn,
    current_user: User = Depends(get_current_user),
    post_dao: PostDAO = Depends(),
    comment_dao: CommentDAO = Depends(),
) -> CommentOut:
    """Create a comment on a visible post (US-3.2).

    Insert and ``posts.comments_count`` increment happen in the same
    transaction (see :class:`CommentDAO.create`).
    """
    post = await _get_visible_post(post_dao, post_id, current_user)
    comment = await comment_dao.create(
        post_id=post.id, user_id=current_user.id, content=body.content
    )
    return _to_comment_out(comment, current_user)


@router.get(
    "/posts/{post_id}/comments",
    response_model=PaginatedComments,
    name="list_comments",
)
async def list_comments(
    post_id: int,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    viewer: User | None = Depends(get_current_user_optional),
    post_dao: PostDAO = Depends(),
    comment_dao: CommentDAO = Depends(),
    session: AsyncSession = Depends(get_db_session),
) -> PaginatedComments:
    """Oldest-first, paginated list of comments on a visible post (US-3.3).

    Anonymous viewers may list comments on published posts; on-moderation
    posts are visible only to their author (404 otherwise).
    """
    post = await post_dao.get_by_id(post_id)
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found."
        )
    is_published = post.status == PostStatus.published
    is_author = viewer is not None and viewer.id == post.user_id
    if not (is_published or is_author):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found."
        )

    offset = (page - 1) * size
    total = await comment_dao.count_for_post(post.id)
    items = await comment_dao.list_for_post(post.id, offset=offset, limit=size)
    authors = await _load_comment_authors(session, items)
    return PaginatedComments(
        items=[_to_comment_out(c, authors[c.user_id]) for c in items],
        total=total,
        page=page,
        size=size,
        has_next=offset + size < total,
    )


@router.delete(
    "/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    name="delete_comment",
)
async def delete_comment(
    comment_id: int,
    current_user: User = Depends(get_current_user),
    comment_dao: CommentDAO = Depends(),
    post_dao: PostDAO = Depends(),
) -> Response:
    """Soft-delete a comment (US-3.4).

    Allowed for the comment's author *or* the parent post's author.  The
    paired counter decrement happens inside ``CommentDAO.soft_delete`` in
    the same transaction.
    """
    comment = await comment_dao.get_by_id(comment_id)
    if comment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found."
        )
    post = await post_dao.get_by_id(comment.post_id)
    is_comment_author = comment.user_id == current_user.id
    is_post_author = post is not None and post.user_id == current_user.id
    if not (is_comment_author or is_post_author):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to delete this comment.",
        )
    await comment_dao.soft_delete(comment)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
