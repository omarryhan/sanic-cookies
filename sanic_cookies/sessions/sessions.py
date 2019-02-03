from .base import BaseSession


class Session(BaseSession):
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
        warn_lock=True
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
            warn_lock=warn_lock
        )

class AuthSession(BaseSession):
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

        session_name='auth',
        warn_lock=True
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
            warn_lock=warn_lock
        )
