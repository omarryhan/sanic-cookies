import ujson
from cryptography.fernet import Fernet, InvalidToken

class InCookieEnc:  # pragma: no cover
    '''
        Encrypted in cookie storage

        EXPERIMENTAL (Use under your own discretion)
        -------------

        key e.g. cryptography.fernet.Fernet.generate_key()
        
        Always use this interface alone without any additional interfaces as it will mess things up
        Just make a new Session object and set this as the master interface and none else
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

    def _decrypt(self, val):
        val = self._ensure_encoded(val)
        try:
            val = self.fernet.decrypt(val)
            if val is not None:
                return self.decoder(val)
        except InvalidToken:
            return {}

    def sid_factory(self):
        return self._encrypt({})

    async def fetch(self, sid, request, cookie_name):
        sid = request.cookies.get(cookie_name)
        if sid is not None:
            return self._decrypt(sid)
        else:
            return {}

    async def store(self, sid, expiry, val, request, cookie_name, session_name):
        if request is not None:
            request[session_name].sid = self._encrypt(val)

    async def delete(self, sid, request, cookie_name, session_name):
        if request is not None:
            request[session_name].sid = self._encrypt(val)
