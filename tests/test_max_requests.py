import pytest

def test_max_requests_limit(client):
    """max_requests=3 时，第 4 次调用必须返回 403"""
    resp = client.post("/api/keys/ephemeral", 
                       json={"ttl_seconds": 60, "max_requests": 3})
    assert resp.status_code == 201
    key = resp.json()["key"]
    
    # 前 3 次成功
    for i in range(3):
        r = client.get("/api/data", headers={"X-API-Key": key})
        assert r.status_code == 200
        # Check remaining requests logic
        # 1st call: remaining was 3. Decr -> 2. Response 2.
        # Loop i=0 -> expect 2. (2-0 = 2). Correct.
        assert r.json()["remaining_requests"] == 2 - i
    
    # 第 4 次失败
    r = client.get("/api/data", headers={"X-API-Key": key})
    assert r.status_code == 403
    # Note: exception handler will be needed to flatten structure
    assert r.json()["error_code"] == "EPHEMERAL_KEY_INVALID"
