import time
import asyncio
import uuid

import ujson


class ExpiringDict(dict):
    def __init__(self):
        dict.__init__(self)
        self.expiry_times = {}

    def set(self, key, expiry, val):
        self[key] = val
        self.expiry_times[key] = time.time() + expiry

    def get(self, key):
        val = dict(self).get(key)
        if val is None:
            return None
        if time.time() > self.expiry_times[key]:
            del self[key]
            del self.expiry_times[key]
            return None
        return val

    def delete(self, key):
        try:
            del self[key]
            del self.expiry_times[key]
        except KeyError:
            return

class InMemory:
    '''
        encoder & decoder:

            e.g. json, ujson, pickle, cpickle, bson, msgpack etc..
            Default ujson
    '''
    def __init__(self, store=ExpiringDict, prefix='session:', cleanup_interval=60*60*1, encoder=ujson.dumps, decoder=ujson.loads, sid_factory=lambda: uuid.uuid4().hex):
        self.prefix = prefix
        self._store = store()
        self.cleanup_interval = cleanup_interval
        self.cleaner = None
        self.encoder = encoder
        self.decoder = decoder
        self.sid_factory = sid_factory

    def init(self):
        # Call after the event loop starts
        # Will not be called by the session interface

        async def clean_up_expired_keys():
            while True:
                await asyncio.sleep(self.cleanup_interval)
                for k, v in list(self._store.items()):
                    if time.time() > self._store.expiry_times[k]:
                        del self._store[k]
                        del self._store.expiry_times[k]

        loop = asyncio.get_event_loop()
        self.cleaner = loop.create_task(clean_up_expired_keys())

    def kill(self):
        if self.cleaner is not None:
            self.cleaner.cancel()

    async def fetch(self, sid, **kwargs):
        val = self._store.get(self.prefix + sid)
        if val is not None:
            return self.decoder(val)

    async def store(self, sid, expiry, val, **kwargs):
        if val is not None:
            val = self.encoder(val)
            self._store.set(
                self.prefix + sid,
                expiry,
                val
            )

    async def delete(self, sid, **kwargs):
        self._store.delete(self.prefix + sid)
