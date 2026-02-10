from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Tuple
from datetime import datetime

class StorageBackend(ABC):
    @abstractmethod
    def create_key(self, key_id: str, info: Dict[str, Any], ttl_seconds: int) -> None:
        """Create a new key with info and initial quotas."""
        pass
    
    @abstractmethod
    def get_key_status(self, key_id: str) -> Optional[Tuple[Dict[str, str], int]]:
        """
        Get key info and remaining count.
        Returns: (info_dict, remaining_count) or None if not found/expired.
        """
        pass
    
    @abstractmethod
    def decrement_remaining(self, key_id: str) -> int:
        """
        Decrement remaining count by 1.
        Returns: The new value.
        """
        pass
    
    @abstractmethod
    def delete_key(self, key_id: str) -> None:
        """Delete key data."""
        pass
    
    @abstractmethod
    def exists(self, key_id: str) -> bool:
        """Check if key exists and is valid."""
        pass
