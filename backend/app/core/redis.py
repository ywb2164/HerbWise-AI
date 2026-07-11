from redis.asyncio import Redis

from app.core.config import get_settings

redis_client: Redis | None = None


def get_redis() -> Redis:
    if redis_client is None:
        raise RuntimeError("Redis client has not been initialized")
    return redis_client


async def open_redis() -> None:
    global redis_client
    if redis_client is None:
        redis_client = Redis.from_url(get_settings().redis_url, decode_responses=True)


async def check_redis() -> None:
    await get_redis().ping()


async def close_redis() -> None:
    global redis_client
    if redis_client is not None:
        await redis_client.aclose()
        redis_client = None
