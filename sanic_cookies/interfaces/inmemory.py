import time


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
    def __init__(self, store=ExpiringDict, prefix='session:'):
        self.prefix = prefix
        self._store = store()

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
