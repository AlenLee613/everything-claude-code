import uuid
import datetime
from app.services.redis_client import redis_client
from app.models import EphemeralKeyCreate, EphemeralKeyResponse, EphemeralKeyStatus
from app.exceptions import KeyInvalidException

class KeyService:
    """
    Service for managing ephemeral keys.
    Handles creation and status retrieval with Redis storage.
    """

    @staticmethod
    def create_key(data: EphemeralKeyCreate) -> EphemeralKeyResponse:
        """
        Create a new ephemeral key with specified TTL and max requests.
        
        Args:
            data (EphemeralKeyCreate): Key creation parameters.
            
        Returns:
            EphemeralKeyResponse: The created key details including the generated key string and expiration time.
        """
        key_id = f"ephem_{uuid.uuid4().hex}"
        # Use UTC to match spec examples (Z suffix implies UTC)
        now = datetime.datetime.now(datetime.timezone.utc)
        expire_at = now + datetime.timedelta(seconds=data.ttl_seconds)
        
        # Redis Logic
        pipe = redis_client.pipeline()
        pipe.hset(f"ephem:{key_id}:info", mapping={
            "created_at": now.isoformat(),
            "ttl_seconds": str(data.ttl_seconds),
            "max_requests": str(data.max_requests)
        })
        pipe.set(f"ephem:{key_id}:remaining", str(data.max_requests))
        pipe.expire(f"ephem:{key_id}:info", data.ttl_seconds)
        pipe.expire(f"ephem:{key_id}:remaining", data.ttl_seconds)
        pipe.execute()

        return EphemeralKeyResponse(
            key=key_id,
            expire_at=expire_at,
            remaining=data.max_requests
        )

    @staticmethod
    def get_key_status(key: str) -> EphemeralKeyStatus:
        """
        Get the current status of an ephemeral key.
        
        Args:
            key (str): The ephemeral key string.
            
        Returns:
            EphemeralKeyStatus: Current expire time and remaining requests.
            
        Raises:
            KeyInvalidException: If the key does not exist or has expired.
        """
        info_key = f"ephem:{key}:info"
        remaining_key = f"ephem:{key}:remaining"

        # Check existence first to fail fast with correct error
        if not redis_client.exists(info_key) or not redis_client.exists(remaining_key):
            raise KeyInvalidException()
        
        info = redis_client.hgetall(info_key)
        remaining = redis_client.get(remaining_key)
        
        if not info or remaining is None:
             raise KeyInvalidException()

        created_at = datetime.datetime.fromisoformat(info["created_at"])
        ttl_seconds = int(info["ttl_seconds"])
        expire_at = created_at + datetime.timedelta(seconds=ttl_seconds)

        return EphemeralKeyStatus(
            key=key,
            expire_at=expire_at,
            remaining=int(remaining)
        )
