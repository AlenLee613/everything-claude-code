from functools import lru_cache
from app.config import settings
from app.services.storage_interface import StorageBackend
from app.services.storage_redis import RedisStorage
from app.services.storage_local import LocalStorage

@lru_cache()
def get_storage() -> StorageBackend:
    if settings.STORAGE_TYPE == "local":
        return LocalStorage()
    else:
        return RedisStorage()
