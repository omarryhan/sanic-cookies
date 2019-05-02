from .gino_asyncpg import GinoAsyncPG
from .aioredis import Aioredis
from .inmemory import InMemory
from .incookie import InCookieEnc

STATIC_SID_COOKIE_INTERFACES = [GinoAsyncPG, Aioredis, InMemory]
