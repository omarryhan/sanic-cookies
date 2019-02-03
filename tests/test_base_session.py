from sanic_cookies.sessions.base import BaseSession
from .common import MockInterface, MockApp, MockSession

def test_middlewares_registered():
    app = MockApp()
    sess = BaseSession(app=app)

    assert len(app.req_middleware) == 1
    assert len(app.res_middleware) == 1