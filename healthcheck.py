#!/usr/bin/env python3
"""
Health check script for Docker container
Verifies that the API is responding correctly
"""

import sys
import requests
import time
from urllib.parse import urljoin


def check_health(base_url="http://localhost:8000", timeout=10, max_retries=3):
    """Check if the API is healthy"""
    health_url = urljoin(base_url, "/health")

    for attempt in range(max_retries):
        try:
            response = requests.get(health_url, timeout=timeout)

            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    print(f"✅ Health check passed: {data}")
                    return True
                else:
                    print(f"❌ Health check failed: {data}")
                    return False
            else:
                print(f"❌ Health check failed with status {response.status_code}")

        except requests.exceptions.ConnectionError:
            print(f"⚠️  Attempt {attempt + 1}: Connection failed, retrying...")
            if attempt < max_retries - 1:
                time.sleep(2)
            continue

        except requests.exceptions.Timeout:
            print(f"⚠️  Attempt {attempt + 1}: Request timed out, retrying...")
            if attempt < max_retries - 1:
                time.sleep(2)
            continue

        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False

    print("❌ Health check failed after all retries")
    return False


if __name__ == "__main__":
    # Get base URL from environment or use default
    import os
    base_url = os.getenv("HEALTH_CHECK_URL", "http://localhost:8000")

    if check_health(base_url):
        sys.exit(0)
    else:
        sys.exit(1)