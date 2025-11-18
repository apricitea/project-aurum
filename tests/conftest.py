"""
Pytest fixtures for Telegram bot tests
Provides shared mocks and test utilities
"""

import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Mock the settings before any imports
mock_settings = Mock()
mock_settings.TELEGRAM_BOT_TOKEN = "test_bot_token"
mock_settings.WEB_APP_URL = "https://example.com"
mock_settings.MARKET_OPEN_TIME = "09:00"
mock_settings.MARKET_LUNCH_START = "12:00"
mock_settings.MARKET_LUNCH_END = "13:30"
mock_settings.MARKET_CLOSE_TIME = "16:00"
mock_settings.is_market_hours = Mock(return_value=False)
mock_settings.get_redis_url = Mock(return_value="redis://localhost:6379")
mock_settings.get_risk_limits = Mock(return_value={
    'max_position_size': 0.20,
    'max_sector_concentration': 0.40,
    'max_drawdown': 0.20
})

# Patch the config module before it's imported
sys.modules['src.api.config'] = Mock(settings=mock_settings)

# Mock aioredis since it's deprecated and code uses it
mock_aioredis = Mock()
mock_aioredis.from_url = Mock(return_value=Mock())
sys.modules['aioredis'] = mock_aioredis

# Mock other missing modules that might be imported
sys.modules['feature_engineering'] = Mock()
sys.modules['feature_engineering'].IDXFeatureEngineer = Mock
sys.modules['model_training'] = Mock()
sys.modules['model_ensemble'] = Mock()
sys.modules['model_ensemble'].IDXQuantitativeModel = Mock
sys.modules['signal_generator'] = Mock()
sys.modules['signal_generator'].SignalGenerator = Mock
sys.modules['signal_generator'].AlertSystem = Mock
sys.modules['main_pipeline'] = Mock()
sys.modules['main_pipeline'].DataCollector = Mock
sys.modules['main_pipeline'].TradingPipeline = Mock
sys.modules['backtesting'] = Mock()

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, date, timedelta
from typing import Dict, Any, List
import json


# ==================== Mock Telegram Objects ====================

@pytest.fixture
def mock_update():
    """Mock Telegram Update object"""
    update = Mock()
    update.effective_chat = Mock()
    update.effective_chat.id = 12345
    update.effective_user = Mock()
    update.effective_user.id = 12345
    update.effective_user.username = "testuser"
    update.message = AsyncMock()
    update.message.reply_text = AsyncMock()
    update.callback_query = None
    return update


@pytest.fixture
def mock_context():
    """Mock Telegram Context object"""
    context = Mock()
    context.args = []
    context.user_data = {}
    context.bot_data = {}
    context.bot = AsyncMock()
    return context


@pytest.fixture
def mock_callback_query(mock_update):
    """Mock Telegram callback query for inline buttons"""
    query = AsyncMock()
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    query.data = ""
    mock_update.callback_query = query
    return mock_update


# ==================== Mock Database ====================

@pytest_asyncio.fixture
async def mock_db_manager():
    """Mock DatabaseManager"""
    db = AsyncMock()

    # Mock connection context manager
    conn_mock = AsyncMock()
    conn_mock.execute = AsyncMock()
    conn_mock.fetchrow = AsyncMock()
    conn_mock.fetch = AsyncMock(return_value=[])

    # Setup context managers
    db.get_connection = AsyncMock()
    db.get_connection.return_value.__aenter__ = AsyncMock(return_value=conn_mock)
    db.get_connection.return_value.__aexit__ = AsyncMock(return_value=None)

    db.get_transaction = AsyncMock()
    db.get_transaction.return_value.__aenter__ = AsyncMock(return_value=conn_mock)
    db.get_transaction.return_value.__aexit__ = AsyncMock(return_value=None)

    # Mock health check
    db.health_check = AsyncMock(return_value=True)

    # Mock fetch methods
    db.fetch_one = AsyncMock()
    db.fetch_all = AsyncMock(return_value=[])
    db.execute = AsyncMock()

    return db


# ==================== Mock Redis ====================

@pytest_asyncio.fixture
async def mock_redis():
    """Mock Redis client"""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock()
    redis.setex = AsyncMock()
    redis.delete = AsyncMock()
    redis.incr = AsyncMock(return_value=1)
    redis.ttl = AsyncMock(return_value=-1)
    redis.expire = AsyncMock()
    redis.close = AsyncMock()
    return redis


# ==================== Mock Services ====================

@pytest_asyncio.fixture
async def mock_signal_service():
    """Mock SignalService"""
    service = AsyncMock()

    # Default signal data
    default_signals = [
        {
            'stock_code': 'BBCA',
            'signal_type': 'BUY',
            'confidence': 0.85,
            'position_size': 0.10,
            'current_price': 8500,
            'sector': 'Finance',
            'technical_score': 0.80,
            'fundamental_score': 0.85,
            'sentiment_score': 0.90,
            'composite_score': 0.85,
            'risk_adjusted': True,
            'generated_at': datetime.now().isoformat()
        },
        {
            'stock_code': 'BMRI',
            'signal_type': 'STRONG_BUY',
            'confidence': 0.92,
            'position_size': 0.15,
            'current_price': 6200,
            'sector': 'Finance',
            'technical_score': 0.90,
            'fundamental_score': 0.88,
            'sentiment_score': 0.95,
            'composite_score': 0.91,
            'risk_adjusted': True,
            'generated_at': datetime.now().isoformat()
        }
    ]

    service.get_daily_signals = AsyncMock(return_value=default_signals)
    service.get_portfolio_summary = AsyncMock(return_value={
        'total_positions': 5,
        'total_market_value': 100000000,
        'total_cost_basis': 95000000,
        'total_unrealized_pnl': 5000000,
        'total_unrealized_pnl_percent': 0.0526,
        'sector_breakdown': {
            'Finance': 0.60,
            'Technology': 0.25,
            'Consumer': 0.15
        },
        'last_updated': datetime.now()
    })
    service.get_current_positions = AsyncMock(return_value=[
        {
            'stock_code': 'BBCA',
            'quantity': 1000,
            'average_price': 8000,
            'current_price': 8500,
            'market_value': 8500000,
            'unrealized_pnl': 500000,
            'unrealized_pnl_percent': 0.0625
        }
    ])
    service.health_check = AsyncMock(return_value={
        'status': 'healthy',
        'model_loaded': True
    })

    return service


@pytest_asyncio.fixture
async def mock_alert_engine():
    """Mock AlertEngine"""
    engine = AsyncMock()
    engine.get_alerts = AsyncMock(return_value=[
        {
            'id': '1',
            'alert_type': 'RISK_BREACH',
            'priority': 'high',
            'message': 'Portfolio risk limit exceeded',
            'stock_code': 'BBCA',
            'created_at': datetime.now()
        }
    ])
    return engine


@pytest_asyncio.fixture
async def mock_auth_manager(mock_db_manager, mock_redis):
    """Mock TelegramAuthManager"""
    from src.api.telegram_auth import TelegramAuthManager

    auth = TelegramAuthManager(mock_db_manager)
    auth.redis_client = mock_redis

    # Mock user data
    mock_user = {
        'id': 'user-123',
        'username': 'testuser',
        'email': 'test@example.com',
        'role': 'user',
        'permissions': {'portfolio.view': True, 'portfolio.modify': True},
        'is_active': True,
        'telegram_username': 'testuser'
    }

    # Replace methods with mocks
    auth.generate_auth_token = AsyncMock(return_value={
        'token': 'test_token_abc123',
        'auth_url': 'https://example.com/auth?token=test_token_abc123',
        'expires_in_minutes': 15,
        'expires_at': (datetime.now() + timedelta(minutes=15)).isoformat()
    })

    auth.verify_auth_token = AsyncMock(return_value=True)
    auth.get_user_by_chat_id = AsyncMock(return_value=mock_user)
    auth.is_authenticated = AsyncMock(return_value=True)
    auth.require_auth = AsyncMock(return_value=mock_user)
    auth.check_permission = AsyncMock(return_value=True)
    auth.revoke_session = AsyncMock(return_value=True)
    auth.log_command_execution = AsyncMock()

    return auth


# ==================== Mock Configuration ====================

@pytest.fixture
def mock_settings():
    """Mock settings configuration"""
    settings = Mock()
    settings.TELEGRAM_BOT_TOKEN = "test_bot_token"
    settings.WEB_APP_URL = "https://example.com"
    settings.MARKET_OPEN_TIME = "09:00"
    settings.MARKET_LUNCH_START = "12:00"
    settings.MARKET_LUNCH_END = "13:30"
    settings.MARKET_CLOSE_TIME = "16:00"
    settings.is_market_hours = Mock(return_value=False)
    settings.get_redis_url = Mock(return_value="redis://localhost:6379")
    settings.get_risk_limits = Mock(return_value={
        'max_position_size': 0.20,
        'max_sector_concentration': 0.40,
        'max_drawdown': 0.20
    })
    return settings


# ==================== Test Data Helpers ====================

@pytest.fixture
def sample_signals():
    """Sample trading signals for testing"""
    return [
        {
            'stock_code': 'BBCA',
            'signal_type': 'BUY',
            'confidence': 0.85,
            'position_size': 0.10,
            'current_price': 8500,
            'sector': 'Finance'
        },
        {
            'stock_code': 'BMRI',
            'signal_type': 'STRONG_BUY',
            'confidence': 0.92,
            'position_size': 0.15,
            'current_price': 6200,
            'sector': 'Finance'
        },
        {
            'stock_code': 'TLKM',
            'signal_type': 'SELL',
            'confidence': 0.75,
            'position_size': 0.05,
            'current_price': 3500,
            'sector': 'Technology'
        }
    ]


@pytest.fixture
def sample_portfolio():
    """Sample portfolio data for testing"""
    return {
        'total_positions': 5,
        'total_market_value': 100000000,
        'total_cost_basis': 95000000,
        'total_unrealized_pnl': 5000000,
        'total_unrealized_pnl_percent': 0.0526,
        'sector_breakdown': {
            'Finance': 0.60,
            'Technology': 0.25,
            'Consumer': 0.15
        },
        'last_updated': datetime.now()
    }


@pytest.fixture
def authenticated_context(mock_context, mock_auth_manager):
    """Context with authenticated user"""
    mock_context.user_data['authenticated_user'] = {
        'id': 'user-123',
        'username': 'testuser',
        'email': 'test@example.com',
        'role': 'user',
        'permissions': {'portfolio.view': True, 'portfolio.modify': True}
    }
    mock_context.user_data['user_id'] = 'user-123'
    mock_context.bot_data['auth_manager'] = mock_auth_manager
    return mock_context


# ==================== Transaction Test Fixtures ====================

@pytest.fixture
def mock_transaction_manager(mock_db_manager, mock_signal_service):
    """Mock TransactionManager"""
    from src.api.telegram_transaction_handlers import TransactionManager

    manager = TransactionManager(mock_db_manager, mock_signal_service)

    # Mock transaction creation
    manager.create_pending_transaction = AsyncMock(return_value={
        'transaction_id': 'txn-123',
        'confirmation_code': 'ABC123',
        'expires_at': datetime.now() + timedelta(minutes=5),
        'type': 'buy',
        'stock_code': 'BBCA',
        'quantity': 1000,
        'price': 8500
    })

    # Mock transaction confirmation
    manager.confirm_transaction = AsyncMock(return_value={
        'action': 'buy',
        'stock_code': 'BBCA',
        'quantity': 1000,
        'price': 8500,
        'total_cost': 8500000,
        'new_position': {
            'stock_code': 'BBCA',
            'quantity': 1000,
            'average_price': 8500
        }
    })

    return manager


@pytest.fixture
def mock_preference_manager(mock_db_manager):
    """Mock PreferenceManager"""
    from src.api.telegram_preferences_handlers import PreferenceManager

    manager = PreferenceManager(mock_db_manager)

    # Mock preferences
    default_prefs = {
        'user_id': 'user-123',
        'alert_types': ['high_confidence', 'risk_breach'],
        'signal_filter': 'all',
        'notification_hours': [9, 10, 11, 14, 15],
        'watchlist': ['BBCA', 'BMRI'],
        'language': 'id'
    }

    manager.get_preferences = AsyncMock(return_value=default_prefs)
    manager.update_alert_types = AsyncMock(return_value=default_prefs)
    manager.update_signal_filter = AsyncMock(return_value=default_prefs)
    manager.update_notification_hours = AsyncMock(return_value=default_prefs)
    manager.add_to_watchlist = AsyncMock(return_value=default_prefs)
    manager.remove_from_watchlist = AsyncMock(return_value=default_prefs)
    manager.clear_watchlist = AsyncMock(return_value={**default_prefs, 'watchlist': []})

    return manager


# ==================== Rate Limiter Fixtures ====================

@pytest.fixture
def mock_rate_limiter(mock_redis):
    """Mock RateLimiter"""
    from src.api.telegram_bot_service import RateLimiter

    limiter = RateLimiter(mock_redis)
    limiter.check_rate_limit = AsyncMock(return_value=True)
    limiter.get_remaining_requests = AsyncMock(return_value={
        'limit': 60,
        'remaining': 50,
        'reset_in_seconds': 30,
        'window_seconds': 60
    })

    return limiter


# ==================== Cleanup ====================

@pytest.fixture(autouse=True)
def reset_mocks():
    """Reset all mocks after each test"""
    yield
    # Cleanup happens automatically with pytest
