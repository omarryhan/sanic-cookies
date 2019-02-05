import ujson

class Aioredis:  # pragma: no cover
    '''
        encoder & decoder:

            e.g. json, ujson, pickle, cpickle, bson, msgpack etc..
            Default ujson
    '''
    def __init__(self, client, prefix='session:', encoder=ujson.dumps, decoder=ujson.loads):  # pragma: no cover
        self.client = client
        self.prefix = prefix
        self.encoder = encoder
        self.decoder = decoder

    async def fetch(self, sid):  # pragma: no cover
        val = await self.client.get(self.prefix + sid)
        if val is not None:
            return self.decoder(val)

    async def store(self, sid, expiry, val):  # pragma: no cover
        if val is not None:
            val = self.encoder(val)
            await self.client.setex(self.prefix + sid, expiry, val)

    async def delete(self, sid):  # pragma: no cover
        await self.client.delete(self.prefix + sid)