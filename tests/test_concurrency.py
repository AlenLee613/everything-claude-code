import pytest
from concurrent.futures import ThreadPoolExecutor

def test_concurrent_requests(client):
    """20 个并发请求，max_requests=10 时，恰好 10 次成功"""
    resp = client.post("/api/keys/ephemeral",
                       json={"ttl_seconds": 60, "max_requests": 10})
    key = resp.json()["key"]
    
    # Helper function for threading
    def make_request(_):
        return client.get("/api/data", headers={"X-API-Key": key})

    with ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(
            make_request,
            range(20)
        ))
    
    success = sum(1 for r in results if r.status_code == 200)
    failed = sum(1 for r in results if r.status_code == 403)
    
    assert success == 10
    # The spec asserts failed == 10.
    # In a race condition with 20 threads, it's possible to fail more or less depending on client behavior? 
    # But with atomic Decr, exactly 10 should succeed (Decr returns 9...0). 
    # Any Decr returning < 0 fails.
    # Since we have 20 requests and 10 quota, 10 must succeed, 10 must fail.
    assert failed == 10
