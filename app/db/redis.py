import redis.asyncio as redis

from app.config import Settings, get_settings

_redis_client: redis.Redis | None = None


def get_redis_client(settings: Settings | None = None) -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        settings = settings or get_settings()
        _redis_client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def close_redis_client() -> None:
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
