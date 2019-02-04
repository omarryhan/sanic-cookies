import pytest

from sanic_cookies import AuthSession
from sanic_cookies.sessions.sessions import _DURATION_KEY, _REMEMBER_ME_KEY
from .common import MockApp, MockInterface, MockSession, MockRequest, MockAuthSession, MockSessionDict


@pytest.mark.asyncio
async def test_login_user():

    # SETUP
    sess = MockAuthSession()
    session_dict = MockSessionDict(session=sess)
    request = MockRequest(session_dict=session_dict)
    AUTH_KEY = 'current_mock_user'
    sess.auth_key = AUTH_KEY
    MOCK_USER = {'id': 1}
    MOCK_DURATION = 123
    MOCK_REMEMBER_ME = False

    assert await sess.current_user(request) is None

    await sess.login_user(request=request, user=MOCK_USER, duration=MOCK_DURATION, remember_me=MOCK_REMEMBER_ME)
    async with request[sess.session_name]:
        assert sess.auth_key == AUTH_KEY
        assert request[sess.session_name][sess.auth_key] == MOCK_USER
        assert request[sess.session_name][_REMEMBER_ME_KEY] == MOCK_REMEMBER_ME
        assert request[sess.session_name][_DURATION_KEY] == MOCK_DURATION

    assert await sess.current_user(request) == MOCK_USER

    await sess.logout_user(request)

    assert await sess.current_user(request) is None

@pytest.mark.asyncio
async def test_login_required():

    # SETUP
    sess = MockAuthSession()
    session_dict = MockSessionDict(session=sess)
    request = MockRequest(session_dict=session_dict)
    AUTH_KEY = 'current_mock_user'
    sess.auth_key = AUTH_KEY
    MOCK_USER = {'id': 2}


    NO_AUTH_MSG = 'NO_AUTH'
    def mock_no_auth_handler(request, *args, **kwargs):
        return NO_AUTH_MSG

    AUTH_MSG = 'AUTH'
    @sess.login_required(no_auth_handler=mock_no_auth_handler)
    def sync_route(request):
        return AUTH_MSG

    @sess.login_required(no_auth_handler=mock_no_auth_handler)
    async def async_route(request):
        return AUTH_MSG

    # Assert no user is logged in
    assert await sess.current_user(request) is None

    # TEST NO AUTH
    assert await async_route(request) == NO_AUTH_MSG
    assert await sync_route(request) == NO_AUTH_MSG

    await sess.login_user(request=request, user=MOCK_USER)
    assert await sess.current_user(request) == MOCK_USER

    # TEST AUTH
    assert await async_route(request) == AUTH_MSG
    assert await async_route(request) == AUTH_MSG

    await sess.logout_user(request)
    assert await sess.current_user(request) is None

    # TEST NO AUTH
    assert await async_route(request) == NO_AUTH_MSG
    assert await sync_route(request) == NO_AUTH_MSG

def test_custom_post_sess():
    # TODO: 
    pass

def test_custom_set_cookie_expiry():
    # TODO: 
    pass