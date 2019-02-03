import ujson
import warnings
from asyncio import Lock
from collections import abc


UNLOCKED_WARNING_MSG = '''
    Updating or reading from session store without acquiring a lock for session ID.
    To avoid race conditions, please use the session dict as follows:

        async with request['session']:
            value = request['session']['foo']
            request['session']['foo'] = 'bar'

    instead of:

        request['session']['foo']
''', RuntimeWarning

class Object:
    pass

class LockKeeper:
    acquired_locks = {}

    async def acquire(self, sid):
        existing_lock = self.acquired_locks.get(sid)
        if existing_lock:
            await existing_lock.acquire()
        else:
            new_lock = Lock()
            await new_lock.acquire()
            self.acquired_locks[sid] = new_lock

    def release(self, sid):
        existing_lock = self.acquired_locks.get(sid)
        if existing_lock:
            existing_lock.release()
            #del self.acquired_locks[sid]

lock_keeper = LockKeeper()

class SessionDict(abc.MutableMapping):

    def __init__(self, initial=None, sid=None, session=None, warn_lock=True):
        self.store = dict(initial or {})
        self.sid = sid
        self.session = session
        self.warn_lock = warn_lock

    def _warn_if_not_locked(self):
        if self.is_locked() is not True and self.warn_lock is True:
            warnings.warn(*UNLOCKED_WARNING_MSG)

    def __getitem__(self, key):  # pragma: no cover
        self._warn_if_not_locked()
        return self.store[key.lower()]

    def __setitem__(self, key, value):  # pragma: no cover
        self._warn_if_not_locked()
        self.store[key.lower()] = value

    def __delitem__(self, key):  # pragma: no cover
        self._warn_if_not_locked()
        del self.store[key.lower()]

    def __iter__(self):  # pragma: no cover
        return iter(self.store)

    def __len__(self):  # pragma: no cover
        return len(self.store)

    def __repr__(self, *args, **kwargs):  # pragma: no cover
        return self.store.__repr__(*args, **kwargs)

    def __str__(self, *args, **kwargs):  # pragma: no cover
        return self.store.__str__(*args, **kwargs)

    def __getattr__(self, key):
        if key in (
            'pop',
            'popitem',
            'update',
            'clear',
            'setdefault'
        ):
            self._warn_if_not_locked()
            return getattr(self.store, key)
        else:
            raise AttributeError(key)

    def is_locked(self):
        if self.sid in lock_keeper.acquired_locks:
            return lock_keeper.acquired_locks[self.sid].locked()
        else:
            return False

    async def __aenter__(self):
        await lock_keeper.acquire(self.sid)
        assert self.is_locked() is True
        initial = await self.session._fetch_sess(self.sid)
        self.store = dict(initial or {})
        return self

    async def __aexit__(self, *args):
        await self.session._post_sess(self.sid, self.store)
        lock_keeper.release(self.sid)
        assert self.is_locked() is False