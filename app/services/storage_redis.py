import redis
import os
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from app.config import settings
from app.services.storage_interface import StorageBackend

class RedisStorage(StorageBackend):
    def __init__(self):
        # Initialize Redis connection
        if os.environ.get("USE_FAKEREDIS") == "true" or settings.USE_FAKEREDIS:
            try:
                from fakeredis import FakeRedis
                self.client = FakeRedis(decode_responses=True)
            except ImportError:
                 # Fallback if fakeredis is not installed but requested (implied by existing code structure)
                 self.client = redis.Redis(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT,
                    decode_responses=True
                )
        else:
            self.client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                decode_responses=True
            )

    def create_key(self, key_id: str, info: Dict[str, Any], ttl_seconds: int) -> None:
        pipe = self.client.pipeline()
        # Ensure info dict values are strings
        str_info = {k: str(v) for k, v in info.items()}
        
        # We need "max_requests" specifically for the logic, assuming it's in info
        initial_remaining = info.get("max_requests", "0")
        
        info_key = f"ephem:{key_id}:info"
        remaining_key = f"ephem:{key_id}:remaining"

        pipe.hset(info_key, mapping=str_info)
        pipe.set(remaining_key, str(initial_remaining))
        pipe.expire(info_key, ttl_seconds)
        pipe.expire(remaining_key, ttl_seconds)
        pipe.execute()

    def get_key_status(self, key_id: str) -> Optional[Tuple[Dict[str, str], int]]:
        info_key = f"ephem:{key_id}:info"
        remaining_key = f"ephem:{key_id}:remaining"

        if not self.client.exists(info_key) or not self.client.exists(remaining_key):
            return None
        
        info = self.client.hgetall(info_key)
        remaining = self.client.get(remaining_key)
        
        if not info or remaining is None:
             return None
             
        return info, int(remaining)

    def decrement_remaining(self, key_id: str) -> int:
        remaining_key = f"ephem:{key_id}:remaining"
        return self.client.decr(remaining_key)

    def delete_key(self, key_id: str) -> None:
        info_key = f"ephem:{key_id}:info"
        remaining_key = f"ephem:{key_id}:remaining"
        self.client.delete(info_key, remaining_key)

    def exists(self, key_id: str) -> bool:
        # We check the 'remaining' key primarily as it's used for rate limiting
        return bool(self.client.exists(f"ephem:{key_id}:remaining"))
