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

    @abstractmethod
    def update_key_policy(self, key_id: str, policy: Dict[str, Any]) -> None:
        """Update IP policy for the key."""
        pass

    @abstractmethod
    def log_usage(self, key_id: str, usage_data: Dict[str, Any]) -> None:
        """Log usage data for a request."""
        pass

    @abstractmethod
    def get_usage_logs(self, start_ts: float, end_ts: float) -> list[Dict[str, Any]]:
        """Get usage logs within a time range."""
        pass

    @abstractmethod
    def set_key_rpm(self, key_id: str, rpm: int) -> None:
        """Set RPM limit for a key."""
        pass

    @abstractmethod
    def check_rate_limit(self, key_id: str, rpm: int) -> bool:
        """Check if key has exceeded RPM limit. Returns True if allowed, False if limited."""
        pass

    @abstractmethod
    def log_attribution(self, log_entry: Dict[str, Any]) -> None:
        """Log detailed attribution data for a request."""
        pass

    @abstractmethod
    def get_attribution_logs(self, filters: Dict[str, Any], page: int = 1, page_size: int = 20) -> Tuple[list[Dict[str, Any]], int]:
        """
        Get attribution logs matching filters.
        Returns: (list_of_logs, total_count)
        """
        pass

