import pytest

from sanic_cookies.models import SessionDict
from .common import MockSession, MockInterface

def test_custom_getattr():
    sess = SessionDict()
    
    for key in (
        'pop',
        'popitem',
        'update',
        'clear',
        'setdefault'
    ):
        assert getattr(sess, key)

    for key in (
        'asd',
        'fasdaif',
        'gapisdaoisd'
    ):
        with pytest.raises(AttributeError):
            getattr(sess, key)


@pytest.mark.asyncio
async def test_aenter_returns_same_instance():
    interface = MockInterface()
    session = MockSession()
    session.set_master_interface(interface)
    sess = SessionDict(sid='asd', session=session)

    async with sess as ret_sess:
        assert ret_sess is sess

@pytest.mark.asyncio
async def test_is_modified():
    sess = SessionDict(session=MockSession(master_interface=MockInterface()), warn_lock=False)
    
    # Doesn't set is_modified upon instantiation
    assert sess.is_modified is False

    # Doesn't set is modified with ctx manager alone
    async with sess:
        pass
    assert sess.is_modified is False

    # sets is_modified False when exiting context manager
    async with sess:
        sess['foo'] = 'bar'
        assert sess.is_modified is True
    assert sess.is_modified is False

    # Sets is_modified on write
    sess['foo'] = 'baz'
    assert sess.is_modified is True

    # Doesn't set is_modified on read
    sess.is_modified = False
    sess['foo']
    assert sess.is_modified is False
