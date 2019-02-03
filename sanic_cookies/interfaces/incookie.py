from cryptography.fernet import Fernet
import ujson

class InCookie:
    '''
    Only to be used with FernetCookie
    Not working (yet)
    '''
    async def fetch(self, sid):
        return sid

    async def delete(self, sid):
        pass

    async def store(self, sid, expiry, val):
        pass