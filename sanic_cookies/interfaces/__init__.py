from .aioredis import Aioredis
from .inmemory import InMemory
from .incookie import InCookieEnc

STATIC_SID_COOKIE_INTERFACES = [Aioredis, InMemory]  # https://bit.ly/1UZD8Q1 (OWASP Privelage Escalation Recommendations)