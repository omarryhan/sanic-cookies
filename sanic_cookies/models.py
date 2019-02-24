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

UNLOCKED_LOCKED_ACCESS_MIX_MSG = '''
    User session has been modified without a context manager all previous changes will be discarded.
    Please stick to using one method of access within the same request.

    e.g. Either:

        async with request['session'] as sess:
            sess['foo'] = 'bar'
        async with request['session'] as sess:
            sess['bar'] = 'baz'

    OR:

        request['session']['foo'] = 'bar'
        request['session']['bar'] = 'baz'

    NOT:

        request['session']['foo'] = 'bar'
        async with request['session'] as sess:
            sess['bar'] = 'baz'

    If you're seeing this warning message, it means that either you or a library you're using
    has tried to modify the session object without a context manager then you discarded the changes 
    that have been made by *correctly* using the async context manager
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
            del self.acquired_locks[sid]

lock_keeper = LockKeeper()

class SessionDict(abc.MutableMapping):
    def __init__(self, initial=None, sid=None, session=None, warn_lock=True, request=None):
        self.store = initial or {}
        self._sid = sid
        self._session = session
        self.warn_lock = warn_lock
        self.request = request
        self.is_modified = False
        self._prev_sid = []
        self.locked_key = None
        self._should_set_cookie = False
        self._should_del_cookie = False

    @property
    def sid(self):
        return self._sid

    @property
    def is_sid_modified(self):
        return bool(self._prev_sid)

    @sid.setter
    def sid(self, val):
        if self._sid is not None:
            self._prev_sid.append(self._sid)
        self._sid = val

    def _warn_if_not_locked(self):
        if self._is_locked() is not True and self.warn_lock is True:
            warnings.warn(*UNLOCKED_WARNING_MSG)

    def __getitem__(self, key):  # pragma: no cover
        self._warn_if_not_locked()
        return self.store[key]

    def __setitem__(self, key, value):  # pragma: no cover
        self._warn_if_not_locked()
        self.is_modified = True
        self.store[key] = value

    def __delitem__(self, key):  # pragma: no cover
        self._warn_if_not_locked()
        self.is_modified = True
        del self.store[key]

    def __iter__(self):  # pragma: no cover
        return iter(self.store)

    def __len__(self):  # pragma: no cover
        return len(self.store)

    def __repr__(self, *args, **kwargs):  # pragma: no cover
        return self.store.__repr__(*args, **kwargs)

    def __str__(self, *args, **kwargs):  # pragma: no cover
        return self.store.__str__(*args, **kwargs)

    def __contains__(self, key):
        return self.store.__contains__(key)

    def __getattr__(self, key):
        if key in (
            'pop',
            'popitem',
            'update',
            'clear',
            'setdefault'
        ):
            self._warn_if_not_locked()
            # is_modified shouldn't be
            # toggled here because when you __getattr__ 
            # you don't actually run the method, But i'll do 
            # anyway for convenience (instead of overriding or wrapping
            # These methods)
            self.is_modified = True
            return getattr(self.store, key)
        else:
            raise AttributeError(key)

    def reset(self):
        if getattr(self, 'store') != {}:
            self._warn_if_not_locked()
            self.store = {}
            self.is_modified = True

    def _is_locked(self):  # used by async ctx man
        ''' Check if there's a locked key from this session dict '''
        if self.locked_key in lock_keeper.acquired_locks:
            return lock_keeper.acquired_locks[self.locked_key].locked()
        else:
            return False

    def is_locked(self):  # should be used by user
        ''' Checks if dict is ready to be locked (Checks sid vs _is_locked, checks self.locked_key) '''
        if self.sid in lock_keeper.acquired_locks:
            return lock_keeper.acquired_locks[self.sid].locked()
        else:
            return False

    async def __aenter__(self):
        if self.is_modified or self.is_sid_modified:
            warnings.warn(
                *UNLOCKED_LOCKED_ACCESS_MIX_MSG
            )
        # While we can always await lock_keeper.acquire(self.sid)
        # self.locked_key will be a better choice to accurately 
        # keep track of the sid that is locked in case sid (and _prev_sid)  
        # is changed in ctx
        await lock_keeper.acquire(self.sid)
        self.locked_key = self.sid
        self.store = await self._session._fetch_sess(self.sid, request=self.request) or {}
        return self

    async def __aexit__(self, *args):
        await self._session._save_sess(self)
        lock_keeper.release(self.locked_key)
        self.locked_key = None

