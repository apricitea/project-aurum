#!/usr/bin/env python3
"""
Comprehensive health check for Project Aurum
Tests API endpoints, authentication, and data consistency
"""

import requests
import time
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

def health_check():
    """Perform comprehensive health check"""
    print("🏥 Project Aurum Health Check")
    print("=" * 50)

    # Test basic API health
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ API Health: HEALTHY")
        else:
            print("❌ API Health: UNHEALTHY")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ API Health: FAILED ({e})")
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

            # Test signals endpoint
            signals_response = requests.get(f"{BASE_URL}/signals/daily", headers=headers, timeout=5)
            if signals_response.status_code == 200:
                signals_data = signals_response.json()
                signal_count = len(signals_data.get("signals", []))
                print(f"✅ Trading Signals: {signal_count} signals available")
            else:
                print("❌ Trading Signals: FAILED")

            # Test portfolio endpoint
            portfolio_response = requests.get(f"{BASE_URL}/portfolio/summary", headers=headers, timeout=5)
            if portfolio_response.status_code == 200:
                portfolio_data = portfolio_response.json()
                total_value = portfolio_data.get("total_value", 0)
                print(f"✅ Portfolio: Rp {total_value:,}")
            else:
                print("❌ Portfolio: FAILED")

            # Test positions endpoint
            positions_response = requests.get(f"{BASE_URL}/portfolio/positions", headers=headers, timeout=5)
            if positions_response.status_code == 200:
                positions_data = positions_response.json()
                position_count = len(positions_data)
                print(f"✅ Positions: {position_count} positions")
            else:
                print("❌ Positions: FAILED")

            # Test market status
            market_response = requests.get(f"{BASE_URL}/market/status", headers=headers, timeout=5)
            if market_response.status_code == 200:
                market_data = market_response.json()
                market_open = market_data.get("market_open", False)
                print(f"✅ Market Status: {'OPEN' if market_open else 'CLOSED'}")
            else:
                print("❌ Market Status: FAILED")

        else:
            print("❌ Authentication: FAILED")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Authentication: ERROR ({e})")
        return False

    # Test invalid authentication
    try:
        invalid_response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"username": "invalid", "password": "invalid"},
            timeout=5
        )
        if invalid_response.status_code == 401:
            print("✅ Auth Security: Invalid credentials properly rejected")
        else:
            print("❌ Auth Security: Security vulnerability detected")
    except requests.exceptions.RequestException:
        print("❌ Auth Security: Test failed")

    # Performance test
    start_time = time.time()
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        response_time = (time.time() - start_time) * 1000
        if response_time < 500:
            print(f"✅ API Performance: {response_time:.1f}ms (EXCELLENT)")
        elif response_time < 1000:
            print(f"⚠️ API Performance: {response_time:.1f}ms (GOOD)")
        else:
            print(f"❌ API Performance: {response_time:.1f}ms (SLOW)")
    except requests.exceptions.RequestException:
        print("❌ API Performance: Test failed")

    print("\n" + "=" * 50)
    print("🎉 Health check completed!")
    print(f"⏰ Timestamp: {datetime.now().isoformat()}")
    return True

if __name__ == "__main__":
    health_check()