import uuid
import datetime
from app.services.storage import get_storage
from app.models import EphemeralKeyCreate, EphemeralKeyResponse, EphemeralKeyStatus, IpPolicy
from app.exceptions import KeyInvalidException

class KeyService:
    """
    Service for managing ephemeral keys.
    Handles creation and status retrieval with storage abstraction.
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
        
        storage = get_storage()
        
        # Prepare Info Dictionary
        info = {
            "created_at": now.isoformat(),
            "ttl_seconds": str(data.ttl_seconds),
            "max_requests": str(data.max_requests)
        }
        
        storage.create_key(key_id, info, data.ttl_seconds)

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
        storage = get_storage()
        
        result = storage.get_key_status(key)
        if not result:
            raise KeyInvalidException()
            
        info, remaining_count = result

        created_at = datetime.datetime.fromisoformat(info["created_at"])
        ttl_seconds = int(info["ttl_seconds"])
        expire_at = created_at + datetime.timedelta(seconds=ttl_seconds)

        return EphemeralKeyStatus(
            key=key,
            expire_at=expire_at,
            remaining=remaining_count
        )

    @staticmethod
    def set_ip_policy(key: str, policy: IpPolicy):
        """
        Set IP policy for an ephemeral key.
        """
        storage = get_storage()
        if not storage.get_key_status(key):
            raise KeyInvalidException()
            
        storage.update_key_policy(key, policy.model_dump())

    @staticmethod
    def set_rpm(key: str, rpm: int):
        """
        Set RPM limit for an ephemeral key.
        """
        storage = get_storage()
        if not storage.get_key_status(key):
            raise KeyInvalidException()
        
        storage.set_key_rpm(key, rpm)

