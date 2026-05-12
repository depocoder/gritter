from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from gritter.db.dao.users_dao import UserDAO
from gritter.services.auth.password import hash_password, verify_password


async def test_create_and_get_by_login(dbsession: AsyncSession) -> None:
    dao = UserDAO(dbsession)
    user = await dao.create(
        first_name="Ada",
        last_name="Lovelace",
        login="ada",
        password_hash=hash_password("analytical-engine"),
    )
    assert user.id is not None
    assert user.created_at is not None

    fetched = await dao.get_by_login("ada")
    assert fetched is not None
    assert fetched.id == user.id


async def test_get_by_login_returns_none_for_unknown(
    dbsession: AsyncSession,
) -> None:
    dao = UserDAO(dbsession)
    assert await dao.get_by_login("ghost") is None


async def test_get_by_login_excludes_soft_deleted(
    dbsession: AsyncSession,
) -> None:
    dao = UserDAO(dbsession)
    user = await dao.create(
        first_name="X",
        last_name="Y",
        login="bye",
        password_hash="h",
    )
    user.deleted_at = datetime.utcnow()
    await dbsession.flush()
    assert await dao.get_by_login("bye") is None


async def test_get_by_id_round_trip(dbsession: AsyncSession) -> None:
    dao = UserDAO(dbsession)
    user = await dao.create(
        first_name="A",
        last_name="B",
        login="ab",
        password_hash="h",
    )
    fetched = await dao.get_by_id(user.id)
    assert fetched is not None
    assert fetched.login == "ab"


async def test_get_by_id_returns_none_for_unknown(
    dbsession: AsyncSession,
) -> None:
    dao = UserDAO(dbsession)
    assert await dao.get_by_id(999_999) is None


async def test_update_password_replaces_hash(dbsession: AsyncSession) -> None:
    dao = UserDAO(dbsession)
    user = await dao.create(
        first_name="A",
        last_name="B",
        login="changepw",
        password_hash=hash_password("old-password"),
    )
    await dao.update_password(user, hash_password("new-password"))
    assert verify_password("new-password", user.password_hash)
    assert not verify_password("old-password", user.password_hash)
