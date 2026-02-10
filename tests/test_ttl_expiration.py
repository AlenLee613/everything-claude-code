import time
import pytest

def test_ttl_expiration(client):
    """ttl_seconds=2 时，2 秒后必须返回 403"""
    resp = client.post("/api/keys/ephemeral",
                       json={"ttl_seconds": 2, "max_requests": 100})
    key = resp.json()["key"]
    
    # 立即调用成功
    assert client.get("/api/data", headers={"X-API-Key": key}).status_code == 200
    
    # 等待超时
    time.sleep(2.5)
    
    # 再次调用失败
    r = client.get("/api/data", headers={"X-API-Key": key})
    assert r.status_code == 403
    assert r.json()["error_code"] == "EPHEMERAL_KEY_INVALID"
