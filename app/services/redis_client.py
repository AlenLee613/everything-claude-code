import redis
import os
from app.config import settings

# Create a Redis client instance
if os.environ.get("USE_FAKEREDIS") == "true":
    from fakeredis import FakeRedis
    redis_client = FakeRedis(decode_responses=True)
else:
    redis_client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        decode_responses=True
    )

def get_redis_client() -> redis.Redis:
    """
    Get the global Redis client instance.
    
    Returns:
        redis.Redis: The configured Redis client.
    """
    return redis_client
