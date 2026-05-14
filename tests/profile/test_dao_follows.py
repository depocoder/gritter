from sqlalchemy.ext.asyncio import AsyncSession

from gritter.db.dao.follows_dao import FollowDAO
from gritter.db.models.users import User


def _user(login: str) -> User:
    return User(first_name="A", last_name="B", login=login, password_hash="x")


async def test_create_then_exists_true(dbsession: AsyncSession) -> None:
    dao = FollowDAO(dbsession)
    a, b = _user("ff-a"), _user("ff-b")
    dbsession.add_all([a, b])
    await dbsession.flush()

    await dao.create(a.id, b.id)

    assert await dao.exists(a.id, b.id) is True


async def test_exists_false_when_no_edge(dbsession: AsyncSession) -> None:
    dao = FollowDAO(dbsession)
    a, b = _user("ff-c"), _user("ff-d")
    dbsession.add_all([a, b])
    await dbsession.flush()

    assert await dao.exists(a.id, b.id) is False


async def test_delete_returns_rowcount_one(dbsession: AsyncSession) -> None:
    dao = FollowDAO(dbsession)
    a, b = _user("ff-e"), _user("ff-f")
    dbsession.add_all([a, b])
    await dbsession.flush()
    await dao.create(a.id, b.id)

    rowcount = await dao.delete(a.id, b.id)

    assert rowcount == 1
    assert await dao.exists(a.id, b.id) is False


async def test_delete_returns_zero_when_no_edge(dbsession: AsyncSession) -> None:
    dao = FollowDAO(dbsession)
    a, b = _user("ff-g"), _user("ff-h")
    dbsession.add_all([a, b])
    await dbsession.flush()

    rowcount = await dao.delete(a.id, b.id)

    assert rowcount == 0


async def test_list_followee_ids_returns_followed(dbsession: AsyncSession) -> None:
    dao = FollowDAO(dbsession)
    me, x, y, z = (_user(s) for s in ("ff-me", "ff-x", "ff-y", "ff-z"))
    dbsession.add_all([me, x, y, z])
    await dbsession.flush()
    await dao.create(me.id, x.id)
    await dao.create(me.id, y.id)

    ids = await dao.list_followee_ids(me.id)

    assert set(ids) == {x.id, y.id}


async def test_list_followee_ids_empty(dbsession: AsyncSession) -> None:
    dao = FollowDAO(dbsession)
    me = _user("ff-empty")
    dbsession.add(me)
    await dbsession.flush()

    ids = await dao.list_followee_ids(me.id)

    assert list(ids) == []
