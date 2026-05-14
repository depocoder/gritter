"""Profile (Эпик 5) endpoints: avatar, follows, feed."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import Response
from loguru import logger
from minio import Minio
from minio.error import MinioException, S3Error

from gritter.db.dao.follows_dao import FollowDAO
from gritter.db.dao.posts_dao import PostDAO
from gritter.db.dao.users_dao import UserDAO
from gritter.db.models.users import User
from gritter.services.avatar import (
    ALLOWED_MIME_TYPES,
    MAX_AVATAR_BYTES,
    fetch_avatar,
    object_key_for,
    public_url_for,
    upload_avatar,
)
from gritter.services.minio.dependency import get_minio_client
from gritter.web.api.auth.dependencies import get_current_user
from gritter.web.api.auth.schema import UserOut
from gritter.web.api.profile.schema import FeedItem, FollowOut, PaginatedFeed

router = APIRouter()

DEFAULT_FEED_PAGE_SIZE = 20
MAX_FEED_PAGE_SIZE = 100


@router.get("/users/me/profile", response_model=UserOut)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
) -> User:
    """Return the current user's profile (US-5.1)."""
    return current_user


@router.post("/users/me/avatar", response_model=UserOut)
async def upload_my_avatar(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    user_dao: UserDAO = Depends(),
    minio_client: Minio = Depends(get_minio_client),
) -> User:
    """Upload an avatar image for the current user (US-5.1)."""
    content_type = file.content_type or ""
    if content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unsupported MIME type: {content_type!r}. "
                f"Allowed: {sorted(ALLOWED_MIME_TYPES)}"
            ),
        )
    data = await file.read()
    if len(data) > MAX_AVATAR_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Avatar exceeds {MAX_AVATAR_BYTES // 1024 // 1024} MB limit.",
        )

    object_key = object_key_for(current_user.id, content_type)
    await upload_avatar(
        minio_client,
        object_key=object_key,
        data=data,
        content_type=content_type,
    )
    await user_dao.update_avatar(current_user, public_url_for(object_key))
    return current_user


@router.post(
    "/users/{user_id}/follow",
    response_model=FollowOut,
    status_code=status.HTTP_201_CREATED,
)
async def follow_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    user_dao: UserDAO = Depends(),
    follow_dao: FollowDAO = Depends(),
) -> FollowOut:
    """Follow `user_id` (US-5.2)."""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot follow yourself.",
        )
    target = await user_dao.get_by_id(user_id)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )
    if await follow_dao.exists(current_user.id, user_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Already following this user.",
        )
    follow = await follow_dao.create(current_user.id, user_id)
    return FollowOut(
        follower_id=follow.follower_id,
        followee_id=follow.followee_id,
        created_at=follow.created_at,
    )


@router.delete("/users/{user_id}/follow", status_code=status.HTTP_204_NO_CONTENT)
async def unfollow_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    follow_dao: FollowDAO = Depends(),
) -> Response:
    """Unfollow `user_id`; 404 if not following (US-5.2)."""
    deleted = await follow_dao.delete(current_user.id, user_id)
    if deleted == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Follow relationship not found.",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/users/me/feed", response_model=PaginatedFeed)
async def get_my_feed(
    page: int = 1,
    size: int = DEFAULT_FEED_PAGE_SIZE,
    current_user: User = Depends(get_current_user),
    follow_dao: FollowDAO = Depends(),
    post_dao: PostDAO = Depends(),
) -> PaginatedFeed:
    """Return published posts from users `current_user` follows (US-5.2)."""
    if page < 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="`page` must be >= 1.",
        )
    if size < 1 or size > MAX_FEED_PAGE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"`size` must be in 1..{MAX_FEED_PAGE_SIZE}.",
        )

    followee_ids = await follow_dao.list_followee_ids(current_user.id)
    total = await post_dao.count_feed(followee_ids)
    offset = (page - 1) * size
    posts = await post_dao.list_feed(followee_ids, offset=offset, limit=size)
    return PaginatedFeed(
        items=[
            FeedItem(
                id=p.id,
                user_id=p.user_id,
                title=p.title,
                content=p.content,
                category=p.category,
                created_at=p.created_at,
            )
            for p in posts
        ],
        total=total,
        page=page,
        size=size,
        has_next=offset + size < total,
    )


@router.get("/avatars/{object_key:path}")
async def serve_avatar(
    object_key: str,
    minio_client: Minio = Depends(get_minio_client),
) -> Response:
    """Serve an avatar from MinIO (US-5.1).

    404 only when MinIO says the object/bucket is missing — other MinIO errors
    become 500 (with the original error logged) instead of silently 404-ing.
    """
    try:
        avatar = await fetch_avatar(minio_client, object_key)
    except S3Error as exc:
        if exc.code in {"NoSuchKey", "NoSuchBucket"}:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Avatar not found."
            ) from exc
        logger.error("MinIO S3Error while serving avatar {}: {}", object_key, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Avatar storage error.",
        ) from exc
    except MinioException as exc:
        logger.error("MinIO error while serving avatar {}: {}", object_key, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Avatar storage error.",
        ) from exc
    return Response(content=avatar.data, media_type=avatar.content_type)
