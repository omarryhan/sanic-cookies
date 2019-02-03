from sanic_cookies import Session


class MockInterface:
    def __init__(self):
        self._store = {}

    async def fetch(self, sid):
        return self._store.get(sid)

    async def store(self, sid, expiry, data):
        self._store[sid] = data

    async def delete(self, sid):
        if sid in self._store:
            del self._store[sid]

class MockApp:
    def __init__(self):
        self.req_middleware = []
        self.res_middleware = []
    
    def register_middleware(self, middleware, attach_to=None):
        if attach_to == 'request':
            self.req_middleware.append(middleware)
        elif attach_to == 'response':
            self.res_middleware = [attach_to] + self.res_middleware
        
class MockSession(Session):
    def __init__(self, *args, **kwargs):
        super().__init__(MockApp(), *args, **kwargs)