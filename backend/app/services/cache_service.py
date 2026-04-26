import json
import hashlib
from typing import Any
import redis.asyncio as aioredis
from app.config import settings


class CacheService:
    def __init__(self):
        self._client: aioredis.Redis | None = None

    async def client(self) -> aioredis.Redis:
        if self._client is None:
            self._client = aioredis.from_url(
                settings.REDIS_URL, encoding="utf-8", decode_responses=True
            )
        return self._client

    async def get(self, key: str) -> Any | None:
        r = await self.client()
        value = await r.get(key)
        if value:
            return json.loads(value)
        return None

    async def set(self, key: str, value: Any, ttl: int = settings.CACHE_TTL) -> None:
        r = await self.client()
        await r.setex(key, ttl, json.dumps(value, default=str))

    async def delete(self, key: str) -> None:
        r = await self.client()
        await r.delete(key)

    async def delete_pattern(self, pattern: str) -> None:
        r = await self.client()
        keys = await r.keys(pattern)
        if keys:
            await r.delete(*keys)

    async def exists(self, key: str) -> bool:
        r = await self.client()
        return bool(await r.exists(key))

    async def increment(self, key: str, ttl: int = 60) -> int:
        r = await self.client()
        pipe = r.pipeline()
        await pipe.incr(key)
        await pipe.expire(key, ttl)
        result = await pipe.execute()
        return result[0]

    @staticmethod
    def make_key(*parts: str) -> str:
        return ":".join(parts)

    @staticmethod
    def hash_key(text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()


cache = CacheService()
