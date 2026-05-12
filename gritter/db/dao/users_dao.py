"""DAO for the `users` table."""

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gritter.db.dependencies import get_db_session
from gritter.db.models.users import User


class UserDAO:
    """Read/write access to users."""

    def __init__(self, session: AsyncSession = Depends(get_db_session)) -> None:
        self.session = session

    async def create(
        self,
        *,
        first_name: str,
        last_name: str,
        login: str,
        password_hash: str,
    ) -> User:
        """Insert and flush a new user; returns the persisted entity."""
        user = User(
            first_name=first_name,
            last_name=last_name,
            login=login,
            password_hash=password_hash,
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def get_by_login(self, login: str) -> User | None:
        """Return the active user with the given login, or None."""
        stmt = select(User).where(User.login == login, User.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> User | None:
        """Return the active user by primary key, or None."""
        stmt = select(User).where(User.id == user_id, User.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_password(self, user: User, new_password_hash: str) -> None:
        """Persist a new password hash on `user`."""
        user.password_hash = new_password_hash
        await self.session.flush()
