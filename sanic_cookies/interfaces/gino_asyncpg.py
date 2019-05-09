import datetime
import ujson
import uuid


class GinoAsyncPG:  # pragma: no cover
    """
        encoder & decoder:

            e.g. json, ujson, pickle, cpickle, bson, msgpack etc..
            Default ujson

        Requires postgres 9.5+ for UPSERT (ON CONFLICT DO UPDATE)
    """

    def __init__(
        self,
        client,
        prefix="session:",
        encoder=ujson.dumps,
        decoder=ujson.loads,
        sid_factory=lambda: uuid.uuid4().hex,
    ):
        self.client = client
        self.prefix = prefix
        self.encoder = encoder
        self.decoder = decoder
        self.sid_factory = sid_factory

    async def fetch(self, sid, **kwargs):
        val = await self.client.scalar(
            "SELECT val FROM sessions WHERE sid = $1 AND expires_at > NOW()", sid
        )
        if val is not None:
            return self.decoder(val)

    async def store(self, sid, expiry, val, **kwargs):
        if val is not None:
            val = self.encoder(val)
            await self.client.scalar(
                "INSERT INTO sessions(created_at, sid, val, expires_at) VALUES(NOW(), $1, $2, $3) ON CONFLICT (sid) DO UPDATE SET val = EXCLUDED.val, expires_at = EXCLUDED.expires_at",  # noqa
                sid,
                val,
                datetime.datetime.utcnow() + datetime.timedelta(seconds=expiry),
            )

    async def delete(self, sid, **kwargs):
        await self.client.scalar("DELETE FROM sessions WHERE sid = $1", sid)
