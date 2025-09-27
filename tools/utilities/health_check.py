#!/usr/bin/env python3
"""
Docker health check for Project Aurum
Simple health check optimized for container environments
"""

import requests
import sys
import os

BASE_URL = "http://localhost:8000"

def health_check():
    """Perform simple health check for Docker container"""
    try:
        # Simple health endpoint check
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        if response.status_code == 200:
            print("✅ API Health: HEALTHY")
            return True
        else:
            print(f"❌ API Health: HTTP {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ API Health: FAILED ({e})")
        return False


def comprehensive_health_check():
    """Perform comprehensive health check (for manual use)"""
    print("🏥 Project Aurum Comprehensive Health Check")
    print("=" * 50)

    # Basic health check first
    if not health_check():
        return False

    # Test authentication
    auth_data = {
        "username": "admin",
        "password": "admin123"
    }

    try:
        auth_response = requests.post(
            f"{BASE_URL}/auth/login",
            json=auth_data,
            timeout=5
        )

        if auth_response.status_code == 200:
            print("✅ Authentication: WORKING")
            token_data = auth_response.json()
            access_token = token_data.get("access_token")

            # Test authenticated endpoints
            headers = {"Authorization": f"Bearer {access_token}"}

            # Test user profile
            profile_response = requests.get(f"{BASE_URL}/auth/me", headers=headers, timeout=5)
            if profile_response.status_code == 200:
                print("✅ User Profile: ACCESSIBLE")
            else:
                print("❌ User Profile: INACCESSIBLE")

        else:
            print("❌ Authentication: FAILED")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Authentication: ERROR ({e})")
        return False

    return True

if __name__ == "__main__":
    # For Docker health check, use simple check and exit with proper code
    if health_check():
        sys.exit(0)  # Success
    else:
        sys.exit(1)  # Failure