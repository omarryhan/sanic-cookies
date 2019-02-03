import time
import uuid

import ujson
from ..models import SessionDict, Object


class BaseSession:
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
        warn_lock=True
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
        
        self.interfaces = []
        if master_interface is not None:
            self.interfaces.append(master_interface)

        if not hasattr(app, 'exts'):
            app.exts = Object()
        setattr(app.exts, self.session_name, self)

        app.register_middleware(
            lambda request: self.open_sess(self, request), 
            attach_to='request'
        )
        app.register_middleware(
            lambda request, response: self.close_sess(self, request, response), 
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
        if overwrite:
            if self.interfaces:
                self.interfaces[0] = interface
            else:
                self.interfaces = []
                self.interfaces.append(interface)
        else:
            self.interfaces = [interface] + self.interfaces

    @property
    def master_interface(self):
        if self.interfaces:
            return self.interfaces[0]
        else:
            return None

    #### ------------- Interface API -------------- ####

    async def _fetch_sess(self, sid):
        val = await self.master_interface.fetch(sid)
        return ujson.loads(val) if val is not None else val

    async def _post_sess(self, sid, val):
        if val is not None:
            val = ujson.dumps(val)
            for interface in self.interfaces:
                await interface.store(sid, self.expiry, val)

    async def _del_sess(self, sid):
        for interface in self.interfaces:
            await interface.delete(sid)

    #### ------------- Helpers ------------ ####

    @staticmethod
    def _calculate_expires(expiry):
        expires = time.time() + expiry
        return time.strftime("%a, %d-%b-%Y %T GMT", time.gmtime(expires))

    def get_sid(self, request, external=True):
        if external:
            return request.cookies.get(self.cookie_name)
        else:
            return request[self.session_name].sid

    #### -------------- Loading --------------- ####

    @staticmethod
    async def open_sess(self, request):
        ''' Sets a session_dict to request '''
        # NOTE: SHOULD NOT RETURN ANY VALUE, unless you know what you're doing
        request[self.session_name] = await self._load_sess(request)

    async def _load_sess(self, request):
        sid = self.get_sid(request, external=True)
        if not sid:
            sid = uuid.uuid4().hex
            session_dict = SessionDict(
                sid=sid,
                session=self,
                warn_lock=self.warn_lock
            )
        else:
            val = await self._fetch_sess(sid)
            if val is not None:
                session_dict = SessionDict(
                    val,
                    sid=sid,
                    session=self,
                    warn_lock=self.warn_lock
                )
            else:
                session_dict = SessionDict(
                    sid=sid,
                    session=self,
                    warn_lock=self.warn_lock
                )
        return session_dict

    #### ------------ Saving --------------- ####

    @staticmethod
    async def close_sess(self, request, response):
        ''' Saves request[session_dict] if set to none or deleted:
        Then should cascade these changes to the response and self.interfaces '''
        # NOTE: SHOULD NOT RETURN ANY VALUE, unless you know what you're doing
        session_dict = request.get(self.session_name)
        if session_dict is not None:
            # TODO: Check if modified
            sid = self.get_sid(request, external=False)
            await self._post_sess(sid, dict(request[self.session_name]))
            self._set_cookie(request, response)
        else:
            # if it was purposefully deleted or set to None
            await self._del_sess(self.get_sid(request, external=True))
            self._del_cookie(request, response)

    #### ------------ Cookie Munching ------------- ####

    def _set_cookie(self, request, response):
        response.cookies[self.cookie_name] = request[self.session_name].sid
        if not self.session_cookie:
            response.cookies[self.cookie_name]['expires'] = self._calculate_expires(self.expiry)
            response.cookies[self.cookie_name]['max-age'] = self.expiry
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
        sid = self.get_sid(request, external=True)
        if sid:
            response.cookies[self.cookie_name] = sid
            response.cookies[self.cookie_name]['expires'] = 0
            response.cookies[self.cookie_name]['max-age'] = 0

