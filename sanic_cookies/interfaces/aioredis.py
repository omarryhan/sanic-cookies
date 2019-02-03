class Aioredis:  # pragma: no cover
    def __init__(self, client, prefix='session:'):  # pragma: no cover
        self.client = client
        self.prefix = prefix

    async def fetch(self, sid):  # pragma: no cover
        return await self.client.get(self.prefix + sid)

    async def store(self, sid, expiry, val):  # pragma: no cover
        await self.client.setex(self.prefix + sid, expiry, val)

    async def delete(self, sid):  # pragma: no cover
        await self.client.delete(self.prefix + sid)