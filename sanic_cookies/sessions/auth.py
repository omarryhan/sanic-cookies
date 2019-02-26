from inspect import iscoroutinefunction
from functools import wraps

import ujson
from sanic.exceptions import abort

from .base import BaseSession
from ..models import SessionDict


__all__ = ['AuthSession', 'login_required']

def default_no_auth_handler(request, *args, **kwargs):
    abort(401)


_REMEMBER_ME_KEY = '_remember_me'
_DURATION_KEY = '_override_expiry'
_EXEMPT_METHODS = set(['OPTIONS'])


def login_required(no_auth_handler=None, session_name='auth_session'):
    def wrapped(fn):
        @wraps(fn)
        async def innerwrap(request, *args, **kwargs):
            self = getattr(request.app.exts, session_name)
            if request.method not in _EXEMPT_METHODS and await self.current_user(request) is None:
                return_function = no_auth_handler or default_no_auth_handler
            else:
                return_function = fn
            if iscoroutinefunction(return_function):
                return await return_function(request, *args, **kwargs)
            else:
                return return_function(request, *args, **kwargs)
        return innerwrap
    return wrapped

class AuthSession(BaseSession):
    '''
    Session with auth helpers

    .. note::

        Remember to tighten cookie security before deploying in production
            e.g. set secure = True etc...

    Arguments:

        auth_key:

            name of the item in which the current_user (logged_in) user will be stored

        no_auth_handler:

            async or sync function that takes: 1 arg (request) when no logged in user is found
            
            .. example::

                no_auth_handler = lambda request: sanic.exceptions.abort(401)

            or

            .. example::

                no_auth_handler = lambda request: sanic.response.redirect(request.app.url_for('index'))
    '''
    def __init__(
        self,
        app,
        master_interface=None,  # Master read

        cookie_name='SECURE_SESSION',
        domain=None,
        expiry=30*24*60*60,
        httponly=None,
        secure=None,
        samesite=True,
        session_cookie=False,
        path=None,
        comment=None,

        session_name='auth_session',
        warn_lock=True,

        auth_key='current_user',
        no_auth_handler=None,
        store_factory=SessionDict,
    ):

        self.auth_key = auth_key
        self.no_auth_handler = no_auth_handler or default_no_auth_handler
        super().__init__(
            app=app,
            master_interface=master_interface,
            cookie_name=cookie_name,
            domain=domain,
            expiry=expiry,
            httponly=httponly,
            secure=secure,
            samesite=samesite,
            session_cookie=session_cookie,
            path=path,
            comment=comment,

            session_name=session_name,
            warn_lock=warn_lock,
            store_factory=store_factory,
        )

    async def login_user(self, request, user, duration=None, remember_me=None, reset_session=True):
        '''
            Don't use this method with an async context manager. Just await it
 
            Duration = Duration to be stored in store (Must be <= to the cookie's expiry i.e. self.expiry)
            Duration defaults to self.expiry (in seconds)
            remember_me (bool): Whether or not this user session will be a session_cookie. Defaults to self.session_cookie
            reset_session: Whether or not to reset the session dict before adding a current user
                         Defaults to persisting data from anonymous user
        '''
        if not user:
            raise TypeError('user must be a truthy value, not: "{}"'.format(user))
        async with request[self.session_name] as sess:
            ## Delete previous SID upon privelage escelation to avoid session fixation attacks
            sess = self.refresh_sid(sess)
            if reset_session is True:
                sess.reset()
            sess[self.auth_key] = user
            if isinstance(remember_me, bool):
                sess[_REMEMBER_ME_KEY] = remember_me
            if isinstance(duration, int):
                sess[_DURATION_KEY] = duration

    # Overriding (to set custom expiry (login_user(duration)))
    async def _post_sess(self, sid, val, request=None, response=None):
        # Get custom expiry
        expiry = val.get(_DURATION_KEY) or self.expiry if val is not None else self.expiry
        [await interface.store(sid, expiry, val, request=request, cookie_name=self.cookie_name, session_name=self.session_name) for interface in self.interfaces]

    # Overriding (to set remember_me)
    async def _set_cookie_expiry(self, request, response):
        async with request[self.session_name] as sess:
            remember_me = sess.get(_REMEMBER_ME_KEY)
            if remember_me is None:
                session_cookie = self.session_cookie
            else:
                session_cookie = not remember_me

            expiry = sess.get(_DURATION_KEY) or self.expiry

        if not session_cookie:
            response.cookies[self.cookie_name]['expires'] = self._calculate_expires(expiry)
            response.cookies[self.cookie_name]['max-age'] = expiry
        return request, response

    async def logout_user(self, request, logout_anon=True):
        ''' logout_anon: Set to false to delete the authenticated session only when
        there's a logged in user '''
        async with request[self.session_name] as sess:
            if logout_anon or (not logout_anon and sess.get(self.auth_key)):
                sess.reset()

    async def current_user(self, request):
        async with request[self.session_name] as sess:
            return sess.get(self.auth_key)

    def login_required(self, no_auth_handler=None):
        return login_required(
            no_auth_handler=no_auth_handler or self.no_auth_handler, 
            session_name=self.session_name
        )
