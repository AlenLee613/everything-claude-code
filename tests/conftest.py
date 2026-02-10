import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.storage import get_storage
from app.services.storage_redis import RedisStorage
from app.services.storage_local import LocalStorage

# Enable FakeRedis before importing app modules
os.environ["USE_FAKEREDIS"] = "true"

@pytest.fixture(scope="function", autouse=True)
def clean_storage():
    """Clean storage before and after each test."""
    storage = get_storage()
    if isinstance(storage, RedisStorage):
        storage.client.flushdb()
    elif isinstance(storage, LocalStorage):
        # Clean local db
        import sqlite3
        try:
             with storage._connect() as conn:
                conn.execute("DELETE FROM ephemeral_keys")
                conn.commit()
        except Exception:
            pass
    yield
    # Cleanup again
    if isinstance(storage, RedisStorage):
        storage.client.flushdb()
    elif isinstance(storage, LocalStorage):
        try:
             with storage._connect() as conn:
                conn.execute("DELETE FROM ephemeral_keys")
                conn.commit()
        except Exception:
            pass

@pytest.fixture
def client():
    return TestClient(app)
