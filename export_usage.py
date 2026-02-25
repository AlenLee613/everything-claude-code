import httpx
import time
import sys
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"

def export_last_hour():
    end_time = int(time.time())
    start_time = int(time.time() - 3600) # 1 hour ago
    
    print(f"Exporting usage from {datetime.fromtimestamp(start_time)} to {datetime.fromtimestamp(end_time)}...")
    
    try:
        url = f"{BASE_URL}/api/usage/export"
        params = {
            "start": start_time,
            "end": end_time,
            "granularity": "hour"
        }
        
        print(f"Requesting: {url} with params {params}")
        resp = httpx.get(url, params=params)
        
        if resp.status_code == 200:
            filename = "usage_export.csv"
            with open(filename, "w", newline="", encoding="utf-8") as f:
                f.write(resp.text)
            print(f"✅ Successfully exported usage data to {filename}")
            print("\nPreview of first 5 lines:")
            print("-" * 40)
            print("\n".join(resp.text.splitlines()[:5]))
            print("-" * 40)
        else:
            print(f"❌ Failed to export: {resp.status_code}")
            print(resp.text)
            
    except Exception as e:
        print(f"❌ Error during export: {e}")

if __name__ == "__main__":
    # Create some dummy data first so the export isn't empty
    print("Generating fresh data for the demo...")
    try:
        # Create a key
        create_resp = httpx.post(f"{BASE_URL}/api/keys/ephemeral", json={"ttl_seconds": 600, "max_requests": 100})
        if create_resp.status_code == 201:
            key = create_resp.json()["key"]
            # Make a few requests
            headers = {"X-API-Key": key}
            httpx.get(f"{BASE_URL}/api/data", headers=headers)
            httpx.get(f"{BASE_URL}/api/data", headers=headers)
            print(f"Generated 2 requests for key {key}")
            # Wait a moment for consistency
            time.sleep(0.5)
    except Exception as e:
        print(f"Warning: Could not generate data: {e}")

    export_last_hour()
