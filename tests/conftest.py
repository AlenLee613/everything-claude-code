import os

# Enable FakeRedis before importing app modules
os.environ["USE_FAKEREDIS"] = "true"

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.redis_client import redis_client

@pytest.fixture(scope="function", autouse=True)
def clean_redis():
    """Clean Redis before and after each test."""
    redis_client.flushdb()
    yield
    redis_client.flushdb()

@pytest.fixture
def client():
    return TestClient(app)
