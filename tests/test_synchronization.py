import sys
import asyncio
from async_timeout import timeout

import pytest

from sanic_cookies.models import SessionDict, lock_keeper
from sanic_cookies import InMemory
from .common import MockInterface, MockSession, MockRequest


@pytest.mark.asyncio
@pytest.mark.parametrize("Interface", [MockInterface, InMemory])
@pytest.mark.parametrize("Session", [MockSession])
async def test_session_dict_locked_by_sid(Session, Interface):
    mock_interface = Interface()
    sess_man = Session(master_interface=mock_interface)
    SID = "sid"
    session_dict = SessionDict(sid=SID, session=sess_man)

    async with session_dict as sess:
        assert lock_keeper.acquired_locks[SID].locked() is True
        sess["foo"] = "bar"
        assert sess["foo"] == "bar"

    sess = await sess_man._fetch_sess(SID)
    assert sess["foo"] == "bar"

    async with session_dict as sess:
        assert sess["foo"] == "bar"
    assert lock_keeper.acquired_locks.get(SID) is None
    # assert lock_keeper.acquired_locks[SID].locked() is False


@pytest.mark.asyncio
@pytest.mark.parametrize("Interface", [MockInterface, InMemory])
@pytest.mark.parametrize("Session", [MockSession])
async def test_warns_with_unlocked_access(Session, Interface):
    sess_man = Session(master_interface=Interface())
    SID = "an_sid"
    session_dict = SessionDict(sid=SID, session=sess_man, warn_lock=True)

    with pytest.warns(RuntimeWarning):
        session_dict["foo"] = "bar"

    with pytest.warns(RuntimeWarning):
        session_dict["foo"]


@pytest.mark.asyncio
@pytest.mark.parametrize("Interface", [MockInterface, InMemory])
@pytest.mark.parametrize("Session", [MockSession])
async def test_only_saves_with_ctx(Session, Interface):
    sess_man = Session(master_interface=Interface())
    SID = "another_sid"
    session_dict = SessionDict(
        sid=SID, session=sess_man, request=MockRequest(), warn_lock=False
    )

    session_dict["foo"] = "bar"

    with pytest.warns(RuntimeWarning):  # Mixed access warning
        async with session_dict as sess:
            # Should find None, because when you access without a context manager
            # the only time it will save is after the response middleware is called
            sess.get("foo") is None


@pytest.mark.asyncio
@pytest.mark.parametrize("Interface", [MockInterface, InMemory])
@pytest.mark.parametrize("Session", [MockSession])
async def test_awaits_locked_session_dict(Session, Interface):
    sess_man = Session(master_interface=Interface())
    SID = "yet_another_sid"
    session_dict = SessionDict(sid=SID, session=sess_man)

    lock = asyncio.Lock()
    await lock.acquire()

    lock_keeper.acquired_locks[SID] = lock

    assert lock_keeper.acquired_locks[SID].locked() is True

    # It seems that there has been a change in the asyncio.Lock implementation
    # In Python 3.8. When there are no awaiters in Py38, the value of _waiters
    # is None and in py37, the value of _waiters is an empty deque
    minor_version = sys.version_info[1]
    if minor_version == 7:
        assert len(lock_keeper.acquired_locks[SID]._waiters) == 0
    else:
        assert lock_keeper.acquired_locks[SID]._waiters is None

    with pytest.raises(asyncio.TimeoutError):
        async with timeout(0.1):
            async with session_dict:
                session_dict["asd"]
                assert len(lock_keeper.acquired_locks[SID]._waiters) == 1
