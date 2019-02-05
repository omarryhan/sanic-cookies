from sanic_cookies import Session, AuthSession
from sanic_cookies import SessionDict


class MockInterface:
    def __init__(self):
        self._store = {}

    async def fetch(self, sid, request=None, cookie_name=None):
        return self._store.get(sid)

    async def store(self, sid, expiry, data, request=None, cookie_name=None, session_name=None):
        self._store[sid] = data

    async def delete(self, sid, request=None, cookie_name=None, session_name=None):
        if sid in self._store:
            del self._store[sid]

class MockExtensions:
    pass

class MockApp:
    def __init__(self):
        self.req_middleware = []
        self.res_middleware = []
        self.exts = MockExtensions()
    
    def register_middleware(self, middleware, attach_to=None):
        if attach_to == 'request':
            self.req_middleware.append(middleware)
        elif attach_to == 'response':
            self.res_middleware = [attach_to] + self.res_middleware
        
class MockSession(Session):
    def __init__(self, app=MockApp(), master_interface=MockInterface(), *args, **kwargs):
        super().__init__(app=app, master_interface=master_interface, *args, **kwargs)

class MockAuthSession(AuthSession):
    def __init__(self, app=MockApp(), master_interface=MockInterface(), *args, **kwargs):
        super().__init__(app=app, master_interface=master_interface, *args, **kwargs)

class MockSessionDict(SessionDict):
    def __init__(self, session=MockSession(), *args, **kwargs):
        super().__init__(session=session, *args, **kwargs)
    
class MockRequest:
    def __init__(self, session_dict=MockSessionDict(), app=MockApp()):
        setattr(self, session_dict.session.session_name, session_dict)
        self.app = app

    def __getitem__(self, k):
        return getattr(self, k)
