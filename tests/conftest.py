"""
Global pytest configuration and fixtures for Project Aurum test suite
"""

import pytest
import asyncio
import os
import tempfile
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
from fastapi.testclient import TestClient
from httpx import AsyncClient
import numpy as np

# Test configuration
os.environ["TESTING"] = "1"
os.environ["LOG_LEVEL"] = "ERROR"

# Mock database connection for tests
pytest_plugins = ["pytest_asyncio"]


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_settings():
    """Mock application settings for testing"""
    from unittest.mock import MagicMock
    settings = MagicMock()
    settings.DATABASE_URL = "sqlite:///:memory:"
    settings.SECRET_KEY = "test-secret-key-for-testing-only"
    settings.ALGORITHM = "HS256"
    settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
    settings.ALLOWED_ORIGINS = ["*"]
    settings.ENVIRONMENT = "test"
    settings.ALPHA_VANTAGE_API_KEY = "test-api-key"
    settings.IDX_API_KEY = "test-idx-key"
    settings.REDIS_URL = "redis://localhost:6379/1"
    return settings


@pytest.fixture
async def mock_db_manager():
    """Mock database manager for testing"""
    mock_db = AsyncMock()
    mock_db.initialize = AsyncMock()
    mock_db.close = AsyncMock()
    mock_db.health_check = AsyncMock()
    mock_db.get_session = AsyncMock()
    return mock_db


@pytest.fixture
def mock_auth_manager():
    """Mock authentication manager for testing"""
    mock_auth = AsyncMock()
    mock_auth.authenticate = AsyncMock()
    mock_auth.refresh_token = AsyncMock()
    mock_auth.verify_token = AsyncMock()
    mock_auth.get_current_user = AsyncMock()
    return mock_auth


@pytest.fixture
def sample_user():
    """Sample user for testing"""
    from unittest.mock import MagicMock
    user = MagicMock()
    user.id = 1
    user.username = "testuser"
    user.email = "test@example.com"
    user.role = "trader"
    user.permissions = ["view_alerts", "create_alerts", "manage_portfolio"]
    user.created_at = datetime.now()
    user.last_login = datetime.now()
    user.has_permission = lambda perm: perm in user.permissions
    return user


@pytest.fixture
def sample_admin_user():
    """Sample admin user for testing"""
    from unittest.mock import MagicMock
    user = MagicMock()
    user.id = 2
    user.username = "admin"
    user.email = "admin@example.com"
    user.role = "admin"
    user.permissions = ["view_alerts", "create_alerts", "manage_portfolio", "generate_signals", "admin_access"]
    user.created_at = datetime.now()
    user.last_login = datetime.now()
    user.has_permission = lambda perm: perm in user.permissions
    return user


@pytest.fixture
def lq45_stocks():
    """Sample LQ45 stocks for testing Indonesian market"""
    return [
        {
            "code": "BBCA",
            "name": "Bank Central Asia Tbk",
            "sector": "Financial Services",
            "market_cap": 1250000000000,  # 1.25T IDR
            "price": 9000,
            "volume": 5000000
        },
        {
            "code": "BBRI",
            "name": "Bank Rakyat Indonesia Tbk",
            "sector": "Financial Services",
            "market_cap": 900000000000,
            "price": 4500,
            "volume": 8000000
        },
        {
            "code": "TLKM",
            "name": "Telekomunikasi Indonesia Tbk",
            "sector": "Telecommunications",
            "market_cap": 750000000000,
            "price": 3500,
            "volume": 6000000
        },
        {
            "code": "ASII",
            "name": "Astra International Tbk",
            "sector": "Automotive",
            "market_cap": 600000000000,
            "price": 6500,
            "volume": 4500000
        },
        {
            "code": "UNVR",
            "name": "Unilever Indonesia Tbk",
            "sector": "Consumer Goods",
            "market_cap": 550000000000,
            "price": 3800,
            "volume": 3000000
        }
    ]


@pytest.fixture
def sample_market_data():
    """Sample market data for testing"""
    dates = pd.date_range(start='2024-01-01', end='2024-01-30', freq='D')
    market_data = {}

    for stock in ["BBCA", "BBRI", "TLKM", "ASII", "UNVR"]:
        np.random.seed(42)  # For reproducible test data
        base_price = {"BBCA": 9000, "BBRI": 4500, "TLKM": 3500, "ASII": 6500, "UNVR": 3800}[stock]

        # Generate realistic price movements
        returns = np.random.normal(0.001, 0.02, len(dates))  # Daily returns
        prices = [base_price]
        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))

        market_data[stock] = pd.DataFrame({
            'date': dates,
            'open': [p * (1 + np.random.normal(0, 0.005)) for p in prices],
            'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
            'close': prices,
            'volume': np.random.randint(1000000, 10000000, len(dates)),
            'turnover': [p * v for p, v in zip(prices, np.random.randint(1000000, 10000000, len(dates)))]
        })

    return market_data


@pytest.fixture
def sample_signals():
    """Sample trading signals for testing"""
    return [
        {
            "id": 1,
            "stock_code": "BBCA",
            "signal_type": "BUY",
            "confidence": 0.85,
            "price_target": 9500,
            "stop_loss": 8500,
            "generated_at": datetime.now(),
            "valid_until": datetime.now() + timedelta(days=1),
            "metadata": {
                "rsi": 30,
                "macd": "bullish_crossover",
                "volume_surge": True,
                "sector_momentum": "positive"
            }
        },
        {
            "id": 2,
            "stock_code": "TLKM",
            "signal_type": "SELL",
            "confidence": 0.78,
            "price_target": 3200,
            "stop_loss": 3600,
            "generated_at": datetime.now(),
            "valid_until": datetime.now() + timedelta(days=1),
            "metadata": {
                "rsi": 75,
                "macd": "bearish_divergence",
                "volume_decline": True,
                "sector_momentum": "negative"
            }
        }
    ]


@pytest.fixture
def sample_alerts():
    """Sample alerts for testing"""
    return [
        {
            "id": 1,
            "alert_type": "PRICE_BREAKOUT",
            "message": "BBCA broke above resistance at IDR 9,200",
            "priority": "HIGH",
            "status": "ACTIVE",
            "created_at": datetime.now(),
            "metadata": {
                "stock_code": "BBCA",
                "breakout_price": 9200,
                "volume_confirmation": True
            }
        },
        {
            "id": 2,
            "alert_type": "RISK_WARNING",
            "message": "Portfolio exposure to financial sector exceeded 40%",
            "priority": "MEDIUM",
            "status": "ACKNOWLEDGED",
            "created_at": datetime.now() - timedelta(hours=2),
            "metadata": {
                "sector": "Financial Services",
                "exposure_percentage": 42.5,
                "threshold": 40.0
            }
        }
    ]


@pytest.fixture
def sample_portfolio():
    """Sample portfolio positions for testing"""
    return [
        {
            "stock_code": "BBCA",
            "quantity": 1000,
            "average_price": Decimal("8800.00"),
            "current_price": Decimal("9000.00"),
            "market_value": Decimal("9000000.00"),
            "unrealized_pnl": Decimal("200000.00"),
            "unrealized_pnl_percent": Decimal("2.27"),
            "weight": Decimal("25.0")
        },
        {
            "stock_code": "BBRI",
            "quantity": 2000,
            "average_price": Decimal("4200.00"),
            "current_price": Decimal("4500.00"),
            "market_value": Decimal("9000000.00"),
            "unrealized_pnl": Decimal("600000.00"),
            "unrealized_pnl_percent": Decimal("7.14"),
            "weight": Decimal("25.0")
        }
    ]


@pytest.fixture
def mock_alpha_vantage_api():
    """Mock Alpha Vantage API responses"""
    with patch('src.api.signal_service.AlphaVantageAPI') as mock:
        mock_api = mock.return_value
        mock_api.get_daily_data = AsyncMock(return_value={
            "BBCA": {
                "2024-01-30": {
                    "open": "8950.00",
                    "high": "9100.00",
                    "low": "8900.00",
                    "close": "9000.00",
                    "volume": "5500000"
                }
            }
        })
        mock_api.get_real_time_quote = AsyncMock(return_value={
            "price": "9000.00",
            "change": "+50.00",
            "change_percent": "0.56%",
            "volume": "5500000"
        })
        yield mock_api


@pytest.fixture
def mock_idx_api():
    """Mock IDX API responses"""
    with patch('src.api.signal_service.IDXAPI') as mock:
        mock_api = mock.return_value
        mock_api.get_stock_data = AsyncMock(return_value={
            "code": "BBCA",
            "name": "Bank Central Asia Tbk",
            "price": 9000,
            "change": 50,
            "change_percent": 0.56,
            "volume": 5500000,
            "market_cap": 1250000000000
        })
        mock_api.get_lq45_list = AsyncMock(return_value=[
            "BBCA", "BBRI", "TLKM", "ASII", "UNVR"
        ])
        yield mock_api


@pytest.fixture
async def test_client():
    """Test client for FastAPI app"""
    from src.api.main import app

    # Override dependencies for testing
    with patch('src.api.main.db_manager'), \
         patch('src.api.main.alert_engine'), \
         patch('src.api.main.signal_service'), \
         patch('src.api.main.risk_monitor'):

        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client


@pytest.fixture
def temp_directory():
    """Temporary directory for testing file operations"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def mock_redis():
    """Mock Redis for caching tests"""
    with patch('redis.Redis') as mock:
        mock_redis = mock.return_value
        mock_redis.get = MagicMock(return_value=None)
        mock_redis.set = MagicMock()
        mock_redis.delete = MagicMock()
        mock_redis.exists = MagicMock(return_value=False)
        yield mock_redis


@pytest.fixture
def jakarta_timezone():
    """Jakarta timezone for Indonesian market testing"""
    import pytz
    return pytz.timezone('Asia/Jakarta')


@pytest.fixture
def market_hours():
    """IDX market hours for testing"""
    return {
        "pre_market": {"start": "08:30", "end": "09:00"},
        "regular": {"start": "09:00", "end": "15:49"},
        "post_market": {"start": "15:49", "end": "16:00"}
    }


# Performance testing fixtures
@pytest.fixture
def performance_thresholds():
    """Performance thresholds for testing"""
    return {
        "api_response_time": 0.5,  # 500ms
        "signal_generation": 30.0,  # 30 seconds
        "alert_processing": 1.0,  # 1 second
        "database_query": 0.1,  # 100ms
        "ml_inference": 5.0  # 5 seconds
    }


# Security testing fixtures
@pytest.fixture
def security_test_data():
    """Security test data for various attack scenarios"""
    return {
        "sql_injection": [
            "'; DROP TABLE users; --",
            "admin'--",
            "admin'/*",
            "1' OR '1'='1",
            "1' UNION SELECT * FROM users--"
        ],
        "xss_payloads": [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "';alert('xss');//"
        ],
        "invalid_tokens": [
            "invalid.jwt.token",
            "Bearer malformed",
            "",
            "expired.token.here"
        ]
    }


@pytest.fixture(autouse=True)
def cleanup_test_data():
    """Automatically cleanup test data after each test"""
    yield
    # Cleanup logic can be added here if needed
    pass