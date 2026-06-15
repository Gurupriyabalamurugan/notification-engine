import redis.asyncio as redis


class IdempotencyService:
    KEY_PREFIX = "idempotency:"

    def __init__(self, redis_client: redis.Redis, *, ttl_seconds: int) -> None:
        self._redis = redis_client
        self._ttl_seconds = ttl_seconds

    def _key(self, idempotency_key: str) -> str:
        return f"{self.KEY_PREFIX}{idempotency_key}"

    async def claim(self, idempotency_key: str) -> bool:
        """Return True when this caller owns the idempotency key (new request)."""
        return bool(
            await self._redis.set(
                self._key(idempotency_key),
                "1",
                nx=True,
                ex=self._ttl_seconds,
            )
        )

    async def release(self, idempotency_key: str) -> None:
        await self._redis.delete(self._key(idempotency_key))
