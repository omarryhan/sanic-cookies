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
