"""Auth endpoints (Epic 1: US-1.1 — US-1.4)."""

from fastapi import APIRouter, Depends, HTTPException, status
from redis.asyncio import ConnectionPool, Redis

from gritter.db.dao.users_dao import UserDAO
from gritter.db.models.users import User
from gritter.services.auth.jwt import encode_access_token
from gritter.services.auth.password import hash_password, verify_password
from gritter.services.auth.refresh import (
    consume_refresh_token,
    issue_refresh_token,
)
from gritter.services.redis.dependency import get_redis_pool
from gritter.web.api.auth.dependencies import get_current_user
from gritter.web.api.auth.schema import (
    ChangePasswordIn,
    LoginIn,
    RefreshIn,
    RegisterIn,
    TokenPair,
    UserOut,
)

router = APIRouter(prefix="/auth", tags=["auth"])


async def _issue_tokens(redis_pool: ConnectionPool, user_id: int) -> TokenPair:
    async with Redis(connection_pool=redis_pool) as redis:
        refresh = await issue_refresh_token(redis, user_id)
    return TokenPair(
        access_token=encode_access_token(user_id),
        refresh_token=refresh,
    )


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    payload: RegisterIn,
    user_dao: UserDAO = Depends(),
) -> User:
    """US-1.1: Register a new user."""
    if await user_dao.get_by_login(payload.login) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Login already taken"
        )
    return await user_dao.create(
        first_name=payload.first_name,
        last_name=payload.last_name,
        login=payload.login,
        password_hash=hash_password(payload.password),
    )


@router.post("/login", response_model=TokenPair)
async def login(
    payload: LoginIn,
    user_dao: UserDAO = Depends(),
    redis_pool: ConnectionPool = Depends(get_redis_pool),
) -> TokenPair:
    """US-1.2: Exchange credentials for an access + refresh token pair."""
    user = await user_dao.get_by_login(payload.login)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    return await _issue_tokens(redis_pool, user.id)


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    payload: RefreshIn,
    redis_pool: ConnectionPool = Depends(get_redis_pool),
) -> TokenPair:
    """US-1.3: Rotate a refresh token; the presented refresh is invalidated."""
    async with Redis(connection_pool=redis_pool) as redis:
        user_id = await consume_refresh_token(redis, payload.refresh_token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    return await _issue_tokens(redis_pool, user_id)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    payload: ChangePasswordIn,
    current_user: User = Depends(get_current_user),
    user_dao: UserDAO = Depends(),
) -> None:
    """US-1.4: Change the current user's password."""
    if not verify_password(payload.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Wrong old password"
        )
    await user_dao.update_password(current_user, hash_password(payload.new_password))
