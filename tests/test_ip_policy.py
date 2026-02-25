import pytest
from app.utils.ip import check_ip_allowed

def test_ip_whitelist():
    policy_ips = ["192.168.1.1/32", "10.0.0.0/24"]
    
    assert check_ip_allowed("192.168.1.1", "whitelist", policy_ips) == True
    assert check_ip_allowed("10.0.0.5", "whitelist", policy_ips) == True
    assert check_ip_allowed("192.168.1.2", "whitelist", policy_ips) == False
    assert check_ip_allowed("8.8.8.8", "whitelist", policy_ips) == False

def test_ip_blacklist():
    policy_ips = ["192.168.1.1/32", "10.0.0.0/24"]
    
    assert check_ip_allowed("192.168.1.1", "blacklist", policy_ips) == False
    assert check_ip_allowed("10.0.0.5", "blacklist", policy_ips) == False
    assert check_ip_allowed("192.168.1.2", "blacklist", policy_ips) == True
    assert check_ip_allowed("8.8.8.8", "blacklist", policy_ips) == True

def test_integration_ip_policy(client):
    # 1. Create Key
    resp = client.post("/api/keys/ephemeral", json={"ttl_seconds": 60, "max_requests": 100})
    key = resp.json()["key"]
    
    # 2. Set Whitelist Policy (only 127.0.0.1 allowed)
    # The TestClient uses internal 'testclient' hostname usually, 
    # but requests usually mocked as 127.0.0.1 or 'testclient'. 
    # Let's see what Starlette TestClient reports. usually 'testclient'.
    # Actually, starlette TestClient sets client.host to 'testclient' by default. 
    # But common to use '127.0.0.1' in checks.
    # Let's verify what the server sees first? 
    # Or just whitelist 'testclient' if it's not an IP?
    # ipaddress module fails on 'testclient'.
    # Starlette TestClient default is 'testclient'.
    # We should override it in the request.
    
    # We can perform requests with specific client info in TestClient?
    # client.get(..., headers=...)
    # The `client` fixture is based on `httpx` or `starlette`? `fastapi.testclient.TestClient` wraps `httpx`.
    # It sends client=('testclient', 50000).
    
    # Let's mock the get_client_ip or use numeric IP for TestClient.
    # We can pass `client` param to `get`? No.
    # We can patch `app.middleware.auth.get_client_ip`
    pass

def test_api_ip_policy_enforcement(client):
    from unittest.mock import patch
    
    # 1. Create Key
    resp = client.post("/api/keys/ephemeral", json={"ttl_seconds": 60, "max_requests": 100})
    key = resp.json()["key"]
    
    # 2. Set Access Policy: Whitelist 1.2.3.4
    client.put(f"/api/keys/{key}/ip_policy", json={
        "mode": "whitelist",
        "ips": ["1.2.3.4/32"]
    })
    
    # 3. Simulate Request from 1.2.3.4 (Authorized)
    with patch("app.middleware.auth.get_client_ip", return_value="1.2.3.4"):
        resp = client.get("/api/data", headers={"X-API-Key": key})
        assert resp.status_code == 200
        
    # 4. Simulate Request from 8.8.8.8 (Unauthorized)
    with patch("app.middleware.auth.get_client_ip", return_value="8.8.8.8"):
        resp = client.get("/api/data", headers={"X-API-Key": key})
        assert resp.status_code == 403
        assert resp.json()["error_code"] == "IP_NOT_ALLOWED"

    # 5. Set Access Policy: Blacklist 1.2.3.0/24
    # Note: We must mock the IP to be allowed (1.2.3.4) to perform this update, 
    # because the key currently has a whitelist that only allows 1.2.3.4.
    with patch("app.middleware.auth.get_client_ip", return_value="1.2.3.4"):
        resp = client.put(f"/api/keys/{key}/ip_policy", json={
            "mode": "blacklist",
            "ips": ["1.2.3.0/24"]
        })
        assert resp.status_code == 200

    # 6. Simulate Request from 1.2.3.4 (Blocked)
    with patch("app.middleware.auth.get_client_ip", return_value="1.2.3.4"):
        resp = client.get("/api/data", headers={"X-API-Key": key})
        assert resp.status_code == 403
        assert resp.json()["error_code"] == "IP_NOT_ALLOWED"
        
    # 7. Simulate Request from 8.8.8.8 (Allowed)
    with patch("app.middleware.auth.get_client_ip", return_value="8.8.8.8"):
        resp = client.get("/api/data", headers={"X-API-Key": key})
        assert resp.status_code == 200
