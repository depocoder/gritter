from sqlalchemy.ext.asyncio import AsyncSession

from gritter.db.dao.users_dao import UserDAO


async def test_update_avatar_persists_url(dbsession: AsyncSession) -> None:
    dao = UserDAO(dbsession)
    user = await dao.create(
        first_name="A",
        last_name="B",
        login="avatar-dao",
        password_hash="x",
    )

    await dao.update_avatar(user, "/api/avatars/users/1/avatar.jpg")

    fetched = await dao.get_by_id(user.id)
    assert fetched is not None
    assert fetched.avatar_url == "/api/avatars/users/1/avatar.jpg"
