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

    def update_key_policy(self, key_id: str, policy: Dict[str, Any]) -> None:
        info_key = f"ephem:{key_id}:info"
        # Serialize policy dict to JSON string for storage in HSET or as separate field
        import json
        policy_json = json.dumps(policy)
        self.client.hset(info_key, "ip_policy", policy_json)

    def log_usage(self, key_id: str, usage_data: Dict[str, Any]) -> None:
        """
        Stub implementation for Redis.
        """
        # For simplicity, we can log to a list or just ignore if not critical for this demo,
        # but to satisfy interface, we do nothing or basic logging.
        # Ideally, we would push to a stream or list.
        # But this feature request specifically asked for CSV export which implies querying.
        # Querying range in Redis is doable with Sorted Set (ZADD usage_logs <timestamp> <json>).
        try:
             import json
             usage_data["key_id"] = key_id # Add key_id to the payload
             self.client.zadd("usage_logs", {json.dumps(usage_data): usage_data["timestamp"]})
        except Exception:
             pass

    def get_usage_logs(self, start_ts: float, end_ts: float) -> list[Dict[str, Any]]:
        try:
            import json
            # ZRANGEBYSCORE usage_logs start end
            logs = self.client.zrangebyscore("usage_logs", start_ts, end_ts)
            return [json.loads(log) for log in logs]
        except Exception:
            return []

    def set_key_rpm(self, key_id: str, rpm: int) -> None:
        info = self.get_key_status(key_id)
        if not info:
             return
             
        info_key = f"ephem:{key_id}:info"
        self.client.hset(info_key, "rpm", str(rpm))

    def check_rate_limit(self, key_id: str, rpm: int) -> bool:
        """
        Rate limit using Redis sliding window (ZSET).
        """
        import time
        now = time.time()
        window_start = now - 60
        req_key = f"ephem:{key_id}:requests"

        pipe = self.client.pipeline()
        pipe.zremrangebyscore(req_key, 0, window_start) # Clean old
        pipe.zcard(req_key) # Count existing
        pipe.zadd(req_key, {str(now): now}) # Add current
        pipe.expire(req_key, 60) # Set expiry
        
        _, current_count, _ = pipe.execute()
        
        # current_count is what was there BEFORE we added the new one.
        if current_count >= rpm:
            # We already had `rpm` requests in the window. Adding one more exceeds limit.
            # We should remove the one we just added since it's rejected.
            self.client.zrem(req_key, str(now))
            return False
            
        return True

    def log_attribution(self, log_entry: Dict[str, Any]) -> None:
        """
        Stub implementation for attribution logging in Redis.
        """
        pass

    def get_attribution_logs(self, filters: Dict[str, Any], page: int = 1, page_size: int = 20) -> Tuple[list[Dict[str, Any]], int]:
        """
        Stub implementation for attribution logs retrieval in Redis.
        """
        return [], 0

