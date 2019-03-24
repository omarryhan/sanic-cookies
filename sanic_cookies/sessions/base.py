import time
from collections import deque

import ujson
import datetime
from ..models import SessionDict, Object
from ..interfaces import STATIC_SID_COOKIE_INTERFACES


class BaseSession:
    '''
    Base Session

    Arguments:

        session_name (str):

            Default: 'session'

            name to be accessed from:
            
                - request[session_name] AND
                - app.exts.{session_name}
    '''
    def __init__(
        self,
        app,
        master_interface=None,  # Master read

        cookie_name='SESSION',
        domain=None,
        expiry=30*24*60*60,
        httponly=None,
        secure=None,
        samesite=None,
        session_cookie=False,
        path=None,
        comment=None,

        session_name='session',
        warn_lock=True,
        store_factory=SessionDict,
    ):
        self.cookie_name = cookie_name
        self.domain = domain
        self.expiry = expiry
        self.httponly = httponly
        self.secure = secure
        self.samesite = samesite
        self.session_cookie = session_cookie
        self.path = path
        self.comment = comment

        self.session_name = session_name
        self.warn_lock = warn_lock
        self.store_factory = store_factory
        
        self.interfaces = deque()
        if master_interface is not None:
            self.interfaces.appendleft(master_interface)

        if not hasattr(app, 'exts'):
            app.exts = Object()
        setattr(app.exts, self.session_name, self)

        app.register_middleware(
            self._open_sess, attach_to='request'
        )
        app.register_middleware(
            self._close_sess, attach_to='response'
        )

    #### ------------ Interface management ------------- ####

    def add_interface(self, interface):
        ''' 
        If a master_interface exists, any interface added here will only be written to 
        and will not be read from. Reading will only be done through the "master_interface" 
        However if no master interface is set, adding an interface here will set it as one'''
        self.interfaces.append(interface)

    def set_master_interface(self, interface, overwrite=True):
        if self.interfaces:
            if overwrite:
                self.interfaces.popleft()
            self.interfaces.appendleft(interface)
        else:
            self.interfaces = deque()
            self.interfaces.appendleft(interface)

    @property
    def master_interface(self):
        if self.interfaces:
            return self.interfaces[0]

    #### ------------- Interface API -------------- ####

    async def _fetch_sess(self, sid, request=None):
        return await self.master_interface.fetch(sid, expiry=self.expiry, request=request, cookie_name=self.cookie_name)

    async def _post_sess(self, sid, val, request=None, response=None):
        [await interface.store(sid, self.expiry, val, request=request, cookie_name=self.cookie_name, session_name=self.session_name) for interface in self.interfaces]

    async def _del_sess(self, sid, request=None, response=None):
        [await interface.delete(sid, request=request, cookie_name=self.cookie_name, session_name=self.session_name) for interface in self.interfaces]

    #### ------------- Helpers ------------ ####

    @staticmethod
    def _calculate_expires(expiry):
        return datetime.datetime.utcnow() + datetime.timedelta(seconds=expiry)
        #expires = time.time() + expiry
        #return time.strftime("%a, %d-%b-%Y %T GMT", time.gmtime(expires))

    def _get_sid(self, request, external=True):
        if external:
            return request.cookies.get(self.cookie_name)
        else:
            return request[self.session_name].sid

    @property
    def _is_static_master_interface(self):
        # Static interfaces don't change their SID automatically when the value of their underlying store changes (Unlike Fernet, which always changes when modified) 
        return True in tuple(map(lambda interface: isinstance(self.master_interface, interface), STATIC_SID_COOKIE_INTERFACES))

    def refresh_sid(self, sess):
        '''
        Important:
        
            - Use this whenever your app does any user-privelage escalation to avoid session fixation attacks 
            - Use this method with an async ctx manager 
            - You don't have to use this with Authsess.login_user. Its already being handled for you
        '''
        if self._is_static_master_interface:
            sess.sid = self.master_interface.sid_factory()
        return sess

    #### -------------- Loading --------------- ####

    async def _open_sess(self, request):
        ''' Sets a session_dict to request '''
        # NOTE: SHOULD NOT RETURN ANY VALUE, unless you know what you're doing
        # TODO: Find a way to optimize session fetching
        # Instead of fetching a session twice, once at the beggining of a request
        # and another when accessing the session with an async ctx manager (locking mechanism),
        # consider adding an "initial_fetch" flag that when set to False, will not fetch
        # the session at request start, but will only fetch it when called by the async ctx man
        #
        # The catch:
        # This can be challenging with the current design of the lib, mainly because:
        # In order to have a request['session'] object we must have an sid,
        # and to have an SID, we must check if it's a valid one, and to check if it's a valid one we have to
        # either have an SID format checker (e.g. UUID format checker, fernet decryptor (also validates sig.))
        # or to actually try and fetch the session dict and see if there's a matching session strored. Maybe both??.
        # If we're going to validate the SID using the second method, then we might as well set it to the request rendering
        # this optimization effort useless.
        # A better way that would allow implementing such optimization with ease is to move the session's async
        # ctx manager to this object instead of the session dict. This would however make it harder for 3rd party 
        # libs to access the session dict
        # and also would make it even harder to have to maintain the current API where you can
        # access the session object via request['session'] at request start
        sid = self._get_sid(request, external=True)
        if not sid:
            sid = self.master_interface.sid_factory()
            request[self.session_name] = self.store_factory(
                sid=sid,
                session=self,
                warn_lock=self.warn_lock,
                request=request
            )
        else:
            initial = await self._fetch_sess(sid, request=request)
            if not initial:
                sid = self.master_interface.sid_factory()
                request[self.session_name] = self.store_factory(
                    sid=sid,
                    session=self,
                    warn_lock=self.warn_lock,
                    request=request
                )
            else:
                request[self.session_name] = self.store_factory(
                    initial=initial,
                    sid=sid,
                    session=self,
                    warn_lock=self.warn_lock,
                    request=request
            )

    #### ------------ Saving --------------- ####

    async def _close_sess(self, request, response):
        # NOTE: SHOULD NOT RETURN ANY VALUE, unless you know what you're doing
        session_dict = request.get(self.session_name)
        await self._save_sess(session_dict, request, response)

    async def _save_sess(self, session_dict, request=None, response=None):
        if session_dict is None:
            await self._del_sess(self._get_sid(request, external=True), request=request)
            if response is not None:
                self._del_cookie(response)
        else:
            request = request or session_dict.request

            # Handle SID modified
            if session_dict.is_sid_modified:
                _prev_sids = session_dict._prev_sid.copy()
                [await self._del_sess(_sid, request=request) for _sid in _prev_sids]
                session_dict._prev_sid = []
                # Shouldn't set cookie here, unless is_modified (which will be checked below)

            # Handle Session dict store modified
            if not session_dict.store and session_dict.is_modified:
                await self._del_sess(session_dict.sid, request)
                session_dict.is_modified = False
                session_dict._should_del_cookie = True

            elif session_dict.is_modified:
                await self._post_sess(session_dict.sid, session_dict.store, request=request)
                session_dict.is_modified = False
                session_dict._should_set_cookie = True

            if response is not None:
                if session_dict._should_del_cookie is True:
                    self._del_cookie(response)

                elif session_dict._should_set_cookie is True:
                    await self._set_cookie(session_dict.sid, request, response)

    #### ------------ Cookie Munching ------------- ####

    async def _set_cookie_expiry(self, request, response):
        if not self.session_cookie:
            response.cookies[self.cookie_name]['expires'] = self._calculate_expires(self.expiry)
            response.cookies[self.cookie_name]['max-age'] = self.expiry
        return request, response

    async def _set_cookie(self, sid, request, response):
        response.cookies[self.cookie_name] = sid
        request, response = await self._set_cookie_expiry(request, response)
        for name, value in {
            'httponly': self.httponly,
            'domain': self.domain,
            'samesite': self.samesite,
            'secure': self.secure,
            'path': self.path,
            'comment': self.comment
        }.items():
            if value is not None:
                response.cookies[self.cookie_name][name] = value

    def _del_cookie(self, response):
        try:
            del response.cookies[self.cookie_name]
        except KeyError:
            pass

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
        store_factory=SessionDict,
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
            store_factory=store_factory,
        )

