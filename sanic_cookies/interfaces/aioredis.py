import ujson
import uuid

class Aioredis:  # pragma: no cover
    '''
        encoder & decoder:

            e.g. json, ujson, pickle, cpickle, bson, msgpack etc..
            Default ujson
    '''
    def __init__(self, client, prefix='session:', encoder=ujson.dumps, decoder=ujson.loads, sid_factory=lambda: uuid.uuid4().hex):
        self.client = client
        self.prefix = prefix
        self.encoder = encoder
        self.decoder = decoder
        self.sid_factory = sid_factory

    async def fetch(self, sid, **kwargs):
        val = await self.client.get(self.prefix + sid)
        if val is not None:
            return self.decoder(val)

    async def store(self, sid, expiry, val, **kwargs):
        if val is not None:
            val = self.encoder(val)
            await self.client.setex(self.prefix + sid, expiry, val)

    async def delete(self, sid, **kwargs):
        await self.client.delete(self.prefix + sid)