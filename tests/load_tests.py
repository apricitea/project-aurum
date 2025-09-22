"""
Load testing configuration for Project Aurum Indonesian Trading System.

This module provides comprehensive load testing scenarios to ensure the system
can handle expected traffic during Indonesian market hours.
"""

import json
import random
import time
from locust import HttpUser, task, between, events
from datetime import datetime
import pytz


class TradingAPIUser(HttpUser):
    """
    Simulates a typical user of the Indonesian Trading System.

    This class models realistic user behavior patterns including:
    - Authentication
    - Market data retrieval
    - Signal monitoring
    - Dashboard interactions
    """

    wait_time = between(1, 5)  # Wait 1-5 seconds between requests
    weight = 3  # Higher weight = more instances of this user type

    def on_start(self):
        """Initialize user session and authenticate."""
        self.auth_token = None
        self.user_id = random.randint(1000, 9999)
        self.authenticate()

    def authenticate(self):
        """Authenticate user and store token."""
        response = self.client.post("/api/v1/auth/login", json={
            "username": f"test_user_{self.user_id}",
            "password": "test_password_123"
        })

        if response.status_code == 200:
            data = response.json()
            self.auth_token = data.get("access_token")
            self.client.headers.update({
                "Authorization": f"Bearer {self.auth_token}"
            })

    @task(10)
    def check_health(self):
        """Health check - most common operation."""
        self.client.get("/health")

    @task(8)
    def get_market_status(self):
        """Check Indonesian market status."""
        self.client.get("/api/v1/market/status")

    @task(6)
    def get_signals(self):
        """Retrieve trading signals."""
        with self.client.get("/api/v1/signals/current", catch_response=True) as response:
            if response.status_code == 200:
                signals = response.json()
                if len(signals.get("signals", [])) > 0:
                    response.success()
                else:
                    response.failure("No signals returned")

    @task(5)
    def get_portfolio_status(self):
        """Check portfolio status."""
        if self.auth_token:
            self.client.get("/api/v1/portfolio/status")

    @task(4)
    def get_market_data(self):
        """Retrieve market data for Indonesian stocks."""
        symbols = ["BBCA", "BBRI", "BMRI", "TLKM", "ASII"]
        symbol = random.choice(symbols)
        self.client.get(f"/api/v1/market/data/{symbol}")

    @task(3)
    def get_historical_data(self):
        """Get historical data for analysis."""
        symbols = ["BBCA", "BBRI", "BMRI"]
        symbol = random.choice(symbols)
        days = random.choice([7, 30, 90])
        self.client.get(f"/api/v1/market/history/{symbol}?days={days}")

    @task(2)
    def update_preferences(self):
        """Update user preferences."""
        if self.auth_token:
            preferences = {
                "notification_enabled": random.choice([True, False]),
                "risk_tolerance": random.choice(["low", "medium", "high"]),
                "preferred_symbols": random.sample(["BBCA", "BBRI", "BMRI", "TLKM"], 2)
            }
            self.client.put("/api/v1/user/preferences", json=preferences)

    @task(1)
    def get_performance_metrics(self):
        """Retrieve performance metrics."""
        if self.auth_token:
            self.client.get("/api/v1/analytics/performance")


class InstitutionalUser(HttpUser):
    """
    Simulates institutional users with higher API usage.

    These users typically:
    - Make more frequent API calls
    - Access bulk data endpoints
    - Use advanced analytics features
    """

    wait_time = between(0.5, 2)  # Faster requests
    weight = 1  # Fewer institutional users

    def on_start(self):
        """Initialize institutional session."""
        self.api_key = f"inst_key_{random.randint(100, 999)}"
        self.client.headers.update({
            "X-API-Key": self.api_key,
            "User-Agent": "InstitutionalClient/1.0"
        })

    @task(15)
    def bulk_market_data(self):
        """Get bulk market data."""
        symbols = ["BBCA", "BBRI", "BMRI", "TLKM", "ASII", "UNVR", "ICBP"]
        symbol_list = ",".join(random.sample(symbols, 5))
        self.client.get(f"/api/v1/market/bulk?symbols={symbol_list}")

    @task(10)
    def streaming_data(self):
        """Simulate streaming data connection."""
        self.client.get("/api/v1/stream/market/live")

    @task(8)
    def advanced_analytics(self):
        """Access advanced analytics endpoints."""
        self.client.get("/api/v1/analytics/correlation-matrix")

    @task(5)
    def risk_metrics(self):
        """Get risk assessment metrics."""
        self.client.get("/api/v1/risk/portfolio-var")

    @task(3)
    def backtest_strategy(self):
        """Run strategy backtesting."""
        strategy_config = {
            "strategy_type": "momentum",
            "lookback_period": 20,
            "symbols": ["BBCA", "BBRI"],
            "start_date": "2023-01-01",
            "end_date": "2023-12-31"
        }
        self.client.post("/api/v1/backtest/run", json=strategy_config)


class MarketDataUser(HttpUser):
    """
    Simulates users primarily consuming market data.

    These users focus on:
    - Real-time price data
    - Market indicators
    - Technical analysis data
    """

    wait_time = between(2, 8)
    weight = 2

    @task(20)
    def get_real_time_prices(self):
        """Get real-time price data."""
        symbols = ["BBCA.JK", "BBRI.JK", "BMRI.JK", "TLKM.JK"]
        symbol = random.choice(symbols)
        self.client.get(f"/api/v1/prices/realtime/{symbol}")

    @task(15)
    def get_technical_indicators(self):
        """Retrieve technical indicators."""
        symbol = random.choice(["BBCA", "BBRI", "BMRI"])
        indicators = random.choice(["sma", "ema", "rsi", "macd"])
        self.client.get(f"/api/v1/technical/{symbol}/{indicators}")

    @task(10)
    def get_market_overview(self):
        """Get market overview data."""
        self.client.get("/api/v1/market/overview")

    @task(8)
    def get_sector_performance(self):
        """Check sector performance."""
        self.client.get("/api/v1/market/sectors")

    @task(5)
    def get_top_movers(self):
        """Get top gaining/losing stocks."""
        self.client.get("/api/v1/market/movers")


# Load testing scenarios for different market conditions
class MarketHoursLoadTest(HttpUser):
    """
    Load test specifically designed for Indonesian market hours (9:00-16:00 WIB).

    Simulates peak trading activity with higher load and more aggressive patterns.
    """

    wait_time = between(0.1, 1)  # Very frequent requests during market hours
    weight = 5  # High load during market hours

    def on_start(self):
        """Check if we're in market hours."""
        jakarta_tz = pytz.timezone('Asia/Jakarta')
        current_time = datetime.now(jakarta_tz)

        # Market hours: 9:00 AM - 4:00 PM WIB
        market_open = current_time.replace(hour=9, minute=0, second=0)
        market_close = current_time.replace(hour=16, minute=0, second=0)

        self.is_market_hours = market_open <= current_time <= market_close
        self.is_weekday = current_time.weekday() < 5  # Monday = 0, Friday = 4

    @task(25)
    def high_frequency_market_data(self):
        """High frequency market data requests during trading hours."""
        if self.is_market_hours and self.is_weekday:
            symbols = ["BBCA", "BBRI", "BMRI", "TLKM", "ASII"]
            for symbol in random.sample(symbols, 3):
                self.client.get(f"/api/v1/market/data/{symbol}/realtime")

    @task(20)
    def order_book_updates(self):
        """Simulate order book data requests."""
        if self.is_market_hours and self.is_weekday:
            symbol = random.choice(["BBCA", "BBRI", "BMRI"])
            self.client.get(f"/api/v1/market/orderbook/{symbol}")

    @task(15)
    def trading_signals_check(self):
        """Frequent signal checking during market hours."""
        self.client.get("/api/v1/signals/live")

    @task(10)
    def portfolio_updates(self):
        """Portfolio value updates."""
        self.client.get("/api/v1/portfolio/realtime-value")


# Event handlers for monitoring and reporting
@events.request.add_listener
def log_request(request_type, name, response_time, response_length, response, context, exception, **kwargs):
    """Log request details for analysis."""
    if exception:
        print(f"Request failed: {name} - {exception}")
    elif response.status_code >= 400:
        print(f"HTTP error: {name} - {response.status_code}")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Initialize load test."""
    print("🚀 Starting load test for Project Aurum")
    print(f"Target host: {environment.host}")

    # Check if target is responding
    import requests
    try:
        response = requests.get(f"{environment.host}/health", timeout=10)
        if response.status_code == 200:
            print("✅ Target system is responsive")
        else:
            print(f"⚠️  Target system returned status {response.status_code}")
    except Exception as e:
        print(f"❌ Could not connect to target system: {e}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Generate load test report."""
    print("📊 Load test completed")

    # Calculate basic statistics
    stats = environment.stats
    total_requests = stats.total.num_requests
    total_failures = stats.total.num_failures

    if total_requests > 0:
        failure_rate = (total_failures / total_requests) * 100
        avg_response_time = stats.total.avg_response_time

        print(f"Total requests: {total_requests}")
        print(f"Total failures: {total_failures}")
        print(f"Failure rate: {failure_rate:.2f}%")
        print(f"Average response time: {avg_response_time:.2f}ms")

        # Performance thresholds for Indonesian trading system
        if avg_response_time > 1000:  # 1 second
            print("⚠️  Average response time exceeds 1 second")

        if failure_rate > 5:  # 5% failure rate
            print("❌ Failure rate exceeds acceptable threshold")

        if failure_rate < 1 and avg_response_time < 500:
            print("✅ Load test passed - system performing well")


# Custom tasks for Indonesian market-specific testing
class IndonesianMarketSpecificUser(HttpUser):
    """
    User class for testing Indonesian market-specific features.
    """

    wait_time = between(1, 3)
    weight = 1

    @task(10)
    def idx_composite_data(self):
        """Get IDX Composite index data."""
        self.client.get("/api/v1/market/index/JKSE")

    @task(8)
    def currency_rates(self):
        """Check USD/IDR exchange rates."""
        self.client.get("/api/v1/market/currency/USDIDR")

    @task(6)
    def bank_stocks_data(self):
        """Focus on major Indonesian bank stocks."""
        banks = ["BBCA", "BBRI", "BMRI", "BBNI"]
        bank = random.choice(banks)
        self.client.get(f"/api/v1/market/data/{bank}")

    @task(5)
    def commodity_prices(self):
        """Check commodity prices relevant to Indonesian market."""
        commodities = ["palm-oil", "coal", "nickel"]
        commodity = random.choice(commodities)
        self.client.get(f"/api/v1/market/commodity/{commodity}")

    @task(3)
    def market_calendar(self):
        """Check Indonesian market trading calendar."""
        self.client.get("/api/v1/market/calendar/indonesia")


if __name__ == "__main__":
    # Configuration for running load tests locally
    print("Load test configuration for Project Aurum")
    print("Use: locust -f load_tests.py --host=http://localhost:8000")
    print("Or: locust -f load_tests.py --host=https://api.aurum-trading.com")