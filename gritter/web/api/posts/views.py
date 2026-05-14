"""Posts (Эпик 2) endpoints: create / read / update / soft-delete."""

from collections.abc import Sequence
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gritter.db.dao.posts_dao import PostDAO
from gritter.db.dao.posts_outbox_dao import PostsOutboxDAO
from gritter.db.dependencies import get_db_session
from gritter.db.models.posts import Post, PostStatus
from gritter.db.models.users import User
from gritter.web.api.auth.dependencies import (
    get_current_user,
    get_current_user_optional,
)
from gritter.web.api.posts.schema import (
    AuthorOut,
    MyPostOut,
    PaginatedMyPosts,
    PaginatedPosts,
    PostCreatedOut,
    PostCreateIn,
    PostOut,
    PostUpdateIn,
)

router = APIRouter()

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


def _to_author_out(author: User) -> AuthorOut:
    return AuthorOut.model_validate(author)


def _to_post_out(post: Post, author: User) -> PostOut:
    return PostOut(
        id=post.id,
        title=post.title,
        content=post.content,
        category=post.category,
        status=post.status,
        sentiment=post.sentiment,
        age_rating=post.age_rating,
        likes_count=post.likes_count,
        comments_count=post.comments_count,
        created_at=post.created_at,
        updated_at=post.updated_at,
        author=_to_author_out(author),
    )


def _to_my_post_out(post: Post, author: User) -> MyPostOut:
    return MyPostOut(
        **_to_post_out(post, author).model_dump(),
        is_on_moderation=(post.status == PostStatus.on_moderation),
    )


async def _load_authors(
    session: AsyncSession, posts: Sequence[Post]
) -> dict[int, User]:
    if not posts:
        return {}
    user_ids = {p.user_id for p in posts}
    result = await session.execute(select(User).where(User.id.in_(user_ids)))
    return {u.id: u for u in result.scalars().all()}


@router.post(
    "/posts",
    response_model=PostCreatedOut,
    status_code=status.HTTP_201_CREATED,
    name="create_post",
)
async def create_post(
    body: PostCreateIn,
    current_user: User = Depends(get_current_user),
    post_dao: PostDAO = Depends(),
    outbox_dao: PostsOutboxDAO = Depends(),
) -> PostCreatedOut:
    """Create a new post and atomically enqueue a `post.created` event (US-2.1)."""
    post = await post_dao.create(
        user_id=current_user.id,
        title=body.title,
        content=body.content,
        category=body.category,
    )
    await outbox_dao.enqueue_created(post.id)
    return PostCreatedOut(id=post.id, status=post.status)


@router.get("/posts", response_model=PaginatedPosts, name="list_posts")
async def list_posts(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    author_id: int | None = Query(default=None),
    category: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    post_dao: PostDAO = Depends(),
    session: AsyncSession = Depends(get_db_session),
) -> PaginatedPosts:
    """Public, paginated list of published posts with optional filters (US-2.2)."""
    offset = (page - 1) * size
    total = await post_dao.count_published(
        author_id=author_id,
        category=category,
        date_from=date_from,
        date_to=date_to,
    )
    posts = await post_dao.list_published(
        offset=offset,
        limit=size,
        author_id=author_id,
        category=category,
        date_from=date_from,
        date_to=date_to,
    )
    authors = await _load_authors(session, posts)
    return PaginatedPosts(
        items=[_to_post_out(p, authors[p.user_id]) for p in posts],
        total=total,
        page=page,
        size=size,
        has_next=offset + size < total,
    )


@router.get("/posts/me", response_model=PaginatedMyPosts, name="list_my_posts")
async def list_my_posts(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    status_filter: PostStatus | None = Query(default=None, alias="status"),
    current_user: User = Depends(get_current_user),
    post_dao: PostDAO = Depends(),
) -> PaginatedMyPosts:
    """Author-only list of own posts in any status (US-2.6)."""
    offset = (page - 1) * size
    total = await post_dao.count_by_author(current_user.id, status=status_filter)
    posts = await post_dao.list_by_author(
        current_user.id, offset=offset, limit=size, status=status_filter
    )
    return PaginatedMyPosts(
        items=[_to_my_post_out(p, current_user) for p in posts],
        total=total,
        page=page,
        size=size,
        has_next=offset + size < total,
    )


def _author_can_view(post: Post, viewer: User | None) -> bool:
    if post.status == PostStatus.published:
        return True
    return viewer is not None and viewer.id == post.user_id


@router.get("/posts/{post_id}", response_model=PostOut, name="get_post")
async def get_post(
    post_id: int,
    viewer: User | None = Depends(get_current_user_optional),
    post_dao: PostDAO = Depends(),
    session: AsyncSession = Depends(get_db_session),
) -> PostOut:
    """Single post; non-author sees only published, author sees any status (US-2.3)."""
    post = await post_dao.get_by_id(post_id)
    if post is None or not _author_can_view(post, viewer):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found."
        )
    authors = await _load_authors(session, [post])
    return _to_post_out(post, authors[post.user_id])


@router.patch("/posts/{post_id}", response_model=PostOut, name="update_post")
async def update_post(
    post_id: int,
    body: PostUpdateIn,
    current_user: User = Depends(get_current_user),
    post_dao: PostDAO = Depends(),
    outbox_dao: PostsOutboxDAO = Depends(),
) -> PostOut:
    """Author-only edit; title/content changes re-trigger moderation (US-2.4)."""
    post = await post_dao.get_by_id(post_id)
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found."
        )
    if post.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not the post's author."
        )
    pre_title, pre_content = post.title, post.content
    await post_dao.reset_for_remoderation(
        post,
        title=body.title,
        content=body.content,
        category=body.category,
    )
    title_or_content_changed = (body.title is not None and body.title != pre_title) or (
        body.content is not None and body.content != pre_content
    )
    if title_or_content_changed:
        await outbox_dao.enqueue_updated(post.id)
    return _to_post_out(post, current_user)


@router.delete(
    "/posts/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    name="delete_post",
)
async def delete_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    post_dao: PostDAO = Depends(),
) -> Response:
    """Author-only soft-delete (US-2.5)."""
    post = await post_dao.get_by_id(post_id)
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found."
        )
    if post.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not the post's author."
        )
    await post_dao.soft_delete(post)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
