import time
import asyncio


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
        del self[key]
        del self.expiry_times[key]

class InMemory:
    def __init__(self, store=ExpiringDict, prefix='session:', cleanup_interval=60*60*1):
        self.prefix = prefix
        self._store = store()
        self.cleanup_interval = cleanup_interval
        self.cleaner = None

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

    async def fetch(self, sid):
        return self._store.get(self.prefix + sid)

    async def delete(self, sid):
        if sid in self._store:
            self._store.delete(self.prefix + sid)

    async def store(self, sid, expiry, val):
        self._store.set(
            self.prefix + sid,
            expiry,
            val
        )
