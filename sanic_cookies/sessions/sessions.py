from inspect import isawaitable
from functools import wraps

import ujson
from sanic.exceptions import abort

from .base import BaseSession
from .. import SessionDict


class Session(BaseSession):
    '''
    Generic Session
    '''
    def __init__(
        self,
        app,
        master_interface=None,  # Master read

        cookie_name='SESSION',
        domain=None,
        expiry=30*24*60*60,
        httponly=False,
        secure=False,
        samesite=False,
        session_cookie=False,
        path=None,
        comment=None,

        session_name='session',
        warn_lock=True,
        store_factory=SessionDict
    ):
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
            store_factory=store_factory
        )

def default_no_auth_handler(request):
    abort(401)

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
        store_factory=SessionDict
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
            store_factory=store_factory
        )

    async def login_user(self, request, user, duration=None, remember_me=True):
        ''' User should be JSON serializable
            Duration = Duration to be stored in store (Must be <= to the cookie's expiry i.e. self.expiry)
            Duration defaults to self.expiry (in seconds)
            Whether or not this user session will be a session_cookie
        '''
        async with request[self.session_name] as sess:
            sess[self.auth_key] = user
            sess['_remember_me'] = remember_me
            if isinstance(duration, int):
                sess['_override_expiry'] = duration

    # Overriding
    async def _post_sess(self, sid, val):
        if val is not None:
            # Get custom expiry
            expiry = val.get('_override_expiry') or self.expiry
            # / Get custom expiry
            val = self.to_json(val)
            for interface in self.interfaces:
                await interface.store(sid, expiry, val)

    # Overriding
    async def _set_cookie_expiry(self, request, response):
        async with request[self.session_name] as sess:
            if sess.get('_remember_me') is False:
                session_cookie = True
            else:
                session_cookie = self.session_cookie
        if not session_cookie:
            response.cookies[self.cookie_name]['expires'] = self._calculate_expires(self.expiry)
            response.cookies[self.cookie_name]['max-age'] = self.expiry
        return request, response

    async def logout_user(self, request):
        async with request[self.session_name] as sess:
            if self.auth_key in sess:
                del sess[self.auth_key]

    async def current_user(self, request):
        async with request[self.session_name] as sess:
            return sess.get(self.auth_key)

    # wrapper
    def login_required(self, no_auth_handler=None):
        ''' No auth handler overrides self.no_auth_handler '''
        def wrapped(fn):
            @wraps(fn)
            async def innerwrap(request, *args, **kwargs):
                user = await self.current_user(request)
                if user is None:
                    no_auth_handler = no_auth_handler or self.no_auth_handler
                    return no_auth_handler(request)
                else:
                    if isawaitable(fn):
                        return await fn(request, *args, **kwargs)
                    else:
                        return fn(request, *args, **kwargs)
            return innerwrap
        return wrapped
