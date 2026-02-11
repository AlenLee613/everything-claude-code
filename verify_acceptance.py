import time
import httpx
import sys

BASE_URL = "http://127.0.0.1:8000"

def print_pass(msg):
    print(f"✅ PASS: {msg}")

def print_fail(msg):
    print(f"❌ FAIL: {msg}")
    sys.exit(1)

def print_info(msg):
    print(f"ℹ️  INFO: {msg}")

def test_max_requests():
    print("\n" + "="*50)
    print("Test Case 1: Max Requests Limit")
    print("="*50)
    
    # 1. Create Key
    max_req = 5
    print_info(f"Creating key with max_requests={max_req}")
    resp = httpx.post(f"{BASE_URL}/api/keys/ephemeral", json={"ttl_seconds": 60, "max_requests": max_req})
    if resp.status_code != 201:
        print_fail(f"Failed to create key: {resp.text}")
    
    key = resp.json()["key"]
    print_pass(f"Key created: {key}")
    
    # 2. Consume max_requests
    for i in range(1, max_req + 1):
        resp = httpx.get(f"{BASE_URL}/api/data", headers={"X-API-Key": key})
        if resp.status_code == 200:
            remaining = resp.json()['remaining_requests']
            print_pass(f"Request {i}/{max_req} success. Remaining: {remaining}")
        else:
            print_fail(f"Request {i}/{max_req} failed unexpectedly: {resp.status_code}")

    # 3. Exceed Limit
    print_info("Attempting request (max_requests + 1)...")
    resp = httpx.get(f"{BASE_URL}/api/data", headers={"X-API-Key": key})
    if resp.status_code == 403:
        error_code = resp.json().get("error_code")
        if error_code == "EPHEMERAL_KEY_INVALID":
            print_pass(f"Request failed as expected with 403 and code {error_code}")
        else:
            print_fail(f"Got 403 but wrong error code: {error_code}")
    else:
        print_fail(f"Expected 403, got {resp.status_code}")

def test_ttl_expiry():
    print("\n" + "="*50)
    print("Test Case 2: TTL Expiration")
    print("="*50)

    # 1. Create Key with short TTL
    ttl = 2
    print_info(f"Creating key with ttl_seconds={ttl}")
    resp = httpx.post(f"{BASE_URL}/api/keys/ephemeral", json={"ttl_seconds": ttl, "max_requests": 10})
    if resp.status_code != 201:
        print_fail(f"Failed to create key: {resp.text}")
    
    key = resp.json()["key"]
    print_pass(f"Key created: {key}")

    # 2. Wait
    sleep_time = ttl + 1
    print_info(f"Sleeping for {sleep_time} seconds...")
    time.sleep(sleep_time)

    # 3. Verify Expiry
    print_info("Attempting request after expiration...")
    resp = httpx.get(f"{BASE_URL}/api/data", headers={"X-API-Key": key})
    
    if resp.status_code == 403:
        error_code = resp.json().get("error_code")
        if error_code == "EPHEMERAL_KEY_INVALID":
             print_pass(f"Request failed as expected with 403 and code {error_code}")
        else:
            print_fail(f"Got 403 but wrong error code: {error_code}")
    else:
        print_fail(f"Expected 403, got {resp.status_code}")

if __name__ == "__main__":
    try:
        # Check health first
        httpx.get(f"{BASE_URL}/health")
    except Exception:
        print_fail("Server is not reachable. Is it running?")
        
    test_max_requests()
    test_ttl_expiry()
    print("\n" + "="*50)
    print("🎉 ALL ACCEPTANCE CRITERIA MET")
    print("="*50)
