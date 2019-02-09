import ujson
from cryptography.fernet import Fernet, InvalidToken

class InCookieEnc:
    '''
        Encrypted in-cookie storage

        key e.g. cryptography.fernet.Fernet.generate_key()
        
        Always use this interface alone without any additional interfaces.
        
        If in doubt, instantiate a new Session object and set this as the master interface and none else
    '''
    def __init__(self, key, encoder=ujson.dumps, decoder=ujson.loads):  # pragma: no cover
        self.fernet = Fernet(key)
        self.encoder = encoder
        self.decoder = decoder

    def _ensure_encoded(self, val):
        # Encodes encoded value (typically bytes, sometime str)
        # e.g. '{}' -> b'{}' NOT {} -> b'{}'
        if not isinstance(val, (bytes, bytearray)):
            try:
                val = val.encode()
            except AttributeError:
                val = b'{}'
        return val

    def _encrypt(self, val):
        if val is not None:
            new_sid = self.encoder(val)
        else:
            new_sid = self.encoder({})
        new_sid = self._ensure_encoded(new_sid)
        return self.fernet.encrypt(new_sid).decode()

    def _decrypt(self, val, ttl):
        val = self._ensure_encoded(val)
        try:
            val = self.fernet.decrypt(val, ttl=ttl)
        except InvalidToken:
            return {}
        else:
            if val is not None:
                return self.decoder(val)

    def sid_factory(self):
        return self._encrypt({})

    async def fetch(self, sid, expiry, request, cookie_name):
        if sid is not None:
            return self._decrypt(sid, expiry)
        else:
            return {}

    async def store(self, sid, expiry, val, request, cookie_name, session_name):
        request[session_name].sid = self._encrypt(val)
        # Shouldn't set is_sid_modified, else it will infinitely loop
        if request[session_name]._prev_sid:
            request[session_name]._prev_sid.pop()

    async def delete(self, sid, request, cookie_name, session_name):
        request[session_name].sid = self.sid_factory()
        # Shouldn't set is_sid_modified, else it will infinitely loop
        if request[session_name]._prev_sid:
            request[session_name]._prev_sid.pop()
