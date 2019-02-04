import time
import uuid
from collections import deque

import ujson
from ..models import SessionDict, Object


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
        store_factory=SessionDict
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
            lambda request: self._open_sess(self, request), 
            attach_to='request'
        )
        app.register_middleware(
            lambda request, response: self._close_sess(self, request, response), 
            attach_to='response'
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
        else:
            return None

    #### ------------- Interface API -------------- ####

    async def _fetch_sess(self, sid):
        val = await self.master_interface.fetch(sid)
        if val is not None:
            return ujson.loads(val)

    async def _post_sess(self, sid, val):
        val = ujson.dumps(val)
        if val is not None:
            [await interface.store(sid, self.expiry, val) for interface in self.interfaces]

    async def _del_sess(self, sid):
        [await interface.delete(sid) for interface in self.interfaces]

    #### ------------- Helpers ------------ ####

    @staticmethod
    def _calculate_expires(expiry):
        expires = time.time() + expiry
        return time.strftime("%a, %d-%b-%Y %T GMT", time.gmtime(expires))

    def _get_sid(self, request, external=True):
        if external:
            return request.cookies.get(self.cookie_name)
        else:
            return request[self.session_name].sid

    #### -------------- Loading --------------- ####

    @staticmethod
    async def _open_sess(self, request):
        ''' Sets a session_dict to request '''
        # NOTE: SHOULD NOT RETURN ANY VALUE, unless you know what you're doing
        request[self.session_name] = await self._load_sess(request)

    async def _load_sess(self, request):
        sid = self._get_sid(request, external=True)
        if not sid:
            sid = uuid.uuid4().hex
            session_dict = self.store_factory(
                sid=sid,
                session=self,
                warn_lock=self.warn_lock
            )
        else:
            val = await self._fetch_sess(sid)
            if val is not None:
                session_dict = self.store_factory(
                    initial=val,
                    sid=sid,
                    session=self,
                    warn_lock=self.warn_lock
                )
            else:
                session_dict = self.store_factory(
                    sid=sid,
                    session=self,
                    warn_lock=self.warn_lock
                )
        return session_dict

    #### ------------ Saving --------------- ####

    @staticmethod
    async def _close_sess(self, request, response):
        ''' Saves request[session_dict] if set to none or deleted:
        Then should cascade these changes to the response and self.interfaces '''
        # NOTE: SHOULD NOT RETURN ANY VALUE, unless you know what you're doing
        session_dict = request.get(self.session_name)
        if session_dict is not None:
            external_sid = self._get_sid(request, external=True)
            internal_sid = self._get_sid(request, external=False)
            if (external_sid != internal_sid) or session_dict.is_modified:
                await self._post_sess(internal_sid, request[self.session_name].json())
                await self._set_cookie(request, response)
        else:
            # if it was purposefully deleted or set to None
            await self._del_sess(self._get_sid(request, external=True))
            self._del_cookie(request, response)

    #### ------------ Cookie Munching ------------- ####

    async def _set_cookie_expiry(self, request, response):
        if not self.session_cookie:
            expires = self._calculate_expires(self.expiry)
            max_age = self.expiry
        else:
            expires = None
            max_age = None
        response.cookies[self.cookie_name]['expires'] = expires
        response.cookies[self.cookie_name]['max-age'] = max_age
        return request, response

    async def _set_cookie(self, request, response):
        response.cookies[self.cookie_name] = request[self.session_name].sid
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

    def _del_cookie(self, request, response):
        sid = self._get_sid(request, external=True)
        if sid:
            response.cookies[self.cookie_name] = sid
            response.cookies[self.cookie_name]['expires'] = 0
            response.cookies[self.cookie_name]['max-age'] = 0

