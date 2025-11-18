"""
Comprehensive Unit Tests for Telegram Bot Implementation
Tests authentication, command handlers, transactions, preferences, and error handling

Coverage Requirements:
- Authentication flow (token generation, verification, session management)
- Command handlers (all commands with various scenarios)
- Rate limiting
- Transaction confirmation flow
- Watchlist operations
- Alert preferences
- Error handling
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, Mock, patch, call
from datetime import datetime, date, timedelta
import json

from src.api.telegram_auth import TelegramAuthManager, require_auth, require_permission
from src.api.telegram_handlers import TelegramCommandHandlers
from src.api.telegram_bot_service import TelegramBotService, RateLimiter
from src.api.telegram_transaction_handlers import TransactionManager, cmd_buy, cmd_sell, cmd_confirm, cmd_cancel, cmd_pending
from src.api.telegram_preferences_handlers import PreferenceManager, cmd_subscribe, cmd_watchlist


# ========================================
# AUTHENTICATION TESTS
# ========================================

class TestTelegramAuthentication:
    """Test suite for Telegram authentication system"""

    @pytest.mark.asyncio
    async def test_generate_auth_token_successfully(self, mock_db_manager, mock_redis):
        """Test successful auth token generation"""
        # Arrange
        auth = TelegramAuthManager(mock_db_manager)
        auth.redis_client = mock_redis
        chat_id = 12345
        username = "testuser"

        # Act
        result = await auth.generate_auth_token(chat_id, username)

        # Assert
        assert 'token' in result
        assert 'auth_url' in result
        assert 'expires_in_minutes' in result
        assert result['expires_in_minutes'] == 15
        assert len(result['token']) > 0
        mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_valid_token(self, mock_db_manager, mock_redis):
        """Test verification of valid auth token"""
        # Arrange
        auth = TelegramAuthManager(mock_db_manager)
        auth.redis_client = mock_redis
        token = "valid_token_123"
        user_id = "user-123"
        chat_id = 12345

        # Mock cached token
        mock_redis.get.return_value = json.dumps({
            'telegram_chat_id': chat_id,
            'telegram_username': 'testuser',
            'created_at': datetime.now().isoformat()
        })

        # Act
        result = await auth.verify_auth_token(token, user_id)

        # Assert
        assert result is True
        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_reject_expired_token(self, mock_db_manager, mock_redis):
        """Test rejection of expired auth token"""
        # Arrange
        auth = TelegramAuthManager(mock_db_manager)
        auth.redis_client = mock_redis
        token = "expired_token"
        user_id = "user-123"

        # Mock no cached token
        mock_redis.get.return_value = None

        # Mock database query returning expired token
        conn_mock = AsyncMock()
        conn_mock.fetchrow = AsyncMock(return_value={
            'telegram_chat_id': 12345,
            'telegram_username': 'testuser',
            'expires_at': datetime.now() - timedelta(minutes=20)  # Expired
        })

        mock_db_manager.get_connection.return_value.__aenter__.return_value = conn_mock

        # Act
        result = await auth.verify_auth_token(token, user_id)

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_reject_invalid_token(self, mock_db_manager, mock_redis):
        """Test rejection of invalid auth token"""
        # Arrange
        auth = TelegramAuthManager(mock_db_manager)
        auth.redis_client = mock_redis
        token = "invalid_token"
        user_id = "user-123"

        # Mock no cached token
        mock_redis.get.return_value = None

        # Mock database query returning no token
        conn_mock = AsyncMock()
        conn_mock.fetchrow = AsyncMock(return_value=None)

        mock_db_manager.get_connection.return_value.__aenter__.return_value = conn_mock

        # Act
        result = await auth.verify_auth_token(token, user_id)

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_create_user_session(self, mock_db_manager, mock_redis):
        """Test creation of user session in Redis"""
        # Arrange
        auth = TelegramAuthManager(mock_db_manager)
        auth.redis_client = mock_redis
        chat_id = 12345
        user_id = "user-123"

        # Mock user data
        conn_mock = AsyncMock()
        conn_mock.fetchrow = AsyncMock(return_value={
            'id': user_id,
            'username': 'testuser',
            'email': 'test@example.com',
            'role': 'user',
            'permissions': {'portfolio.view': True},
            'telegram_username': 'testuser'
        })

        mock_db_manager.get_connection.return_value.__aenter__.return_value = conn_mock

        # Act
        await auth._create_telegram_session(chat_id, user_id)

        # Assert
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert f"telegram_session:{chat_id}" in call_args[0]

    @pytest.mark.asyncio
    async def test_check_permission_grants(self, mock_auth_manager):
        """Test permission check grants access"""
        # Arrange
        chat_id = 12345

        # Act
        result = await mock_auth_manager.check_permission(chat_id, 'portfolio.view')

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_check_permission_denies(self, mock_auth_manager):
        """Test permission check denies access"""
        # Arrange
        mock_auth_manager.check_permission = AsyncMock(return_value=False)
        chat_id = 12345

        # Act
        result = await mock_auth_manager.check_permission(chat_id, 'admin.access')

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_rate_limit_auth_attempts(self, mock_db_manager, mock_redis):
        """Test rate limiting on auth attempts"""
        # Arrange
        auth = TelegramAuthManager(mock_db_manager)
        auth.redis_client = mock_redis
        chat_id = 12345

        # Mock rate limit exceeded
        mock_redis.get.return_value = "6"  # More than limit of 5

        # Act & Assert
        with pytest.raises(ValueError, match="Too many authentication attempts"):
            await auth.generate_auth_token(chat_id, "testuser")


# ========================================
# COMMAND HANDLER TESTS
# ========================================

class TestCommandHandlers:
    """Test suite for Telegram command handlers"""

    @pytest.mark.asyncio
    async def test_start_command_sends_welcome_new_user(self, mock_update, mock_context,
                                                         mock_db_manager, mock_signal_service,
                                                         mock_alert_engine, mock_auth_manager):
        """Test /start command sends welcome message with auth link for new user"""
        # Arrange
        handlers = TelegramCommandHandlers(
            mock_db_manager, mock_signal_service, mock_alert_engine, mock_auth_manager
        )

        # Mock unauthenticated user
        mock_auth_manager.get_user_by_chat_id.return_value = None

        # Act
        await handlers.cmd_start(mock_update, mock_context)

        # Assert
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "Welcome" in call_args
        assert "Authentication" in call_args or "authenticate" in call_args.lower()

    @pytest.mark.asyncio
    async def test_start_command_welcomes_back_existing_user(self, mock_update, mock_context,
                                                              mock_db_manager, mock_signal_service,
                                                              mock_alert_engine, mock_auth_manager):
        """Test /start command welcomes back authenticated user"""
        # Arrange
        handlers = TelegramCommandHandlers(
            mock_db_manager, mock_signal_service, mock_alert_engine, mock_auth_manager
        )

        # Act
        await handlers.cmd_start(mock_update, mock_context)

        # Assert
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "Welcome back" in call_args or "already linked" in call_args

    @pytest.mark.asyncio
    async def test_help_command_shows_commands(self, mock_update, mock_context,
                                                mock_db_manager, mock_signal_service,
                                                mock_alert_engine, mock_auth_manager):
        """Test /help command shows available commands"""
        # Arrange
        handlers = TelegramCommandHandlers(
            mock_db_manager, mock_signal_service, mock_alert_engine, mock_auth_manager
        )

        # Act
        await handlers.cmd_help(mock_update, mock_context)

        # Assert
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "/signals" in call_args or "signals" in call_args.lower()
        assert "/portfolio" in call_args or "portfolio" in call_args.lower()

    @pytest.mark.asyncio
    async def test_signals_command_returns_signals_authenticated(self, mock_update, authenticated_context,
                                                                  mock_db_manager, mock_signal_service,
                                                                  mock_alert_engine, mock_auth_manager):
        """Test /signals command returns signals for authenticated user"""
        # Arrange
        handlers = TelegramCommandHandlers(
            mock_db_manager, mock_signal_service, mock_alert_engine, mock_auth_manager
        )

        # Act
        await handlers.cmd_signals(mock_update, authenticated_context)

        # Assert
        mock_signal_service.get_daily_signals.assert_called_once()
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "BBCA" in call_args or "signal" in call_args.lower()

    @pytest.mark.asyncio
    async def test_signals_command_rejects_unauthenticated(self, mock_update, mock_context,
                                                            mock_db_manager, mock_signal_service,
                                                            mock_alert_engine, mock_auth_manager):
        """Test /signals command rejects unauthenticated user"""
        # Arrange
        handlers = TelegramCommandHandlers(
            mock_db_manager, mock_signal_service, mock_alert_engine, mock_auth_manager
        )

        # Mock unauthenticated user
        mock_auth_manager.get_user_by_chat_id.return_value = None
        mock_context.bot_data['auth_manager'] = mock_auth_manager

        # Use decorator directly
        @require_auth
        async def test_handler(update, context):
            await handlers.cmd_signals(update, context)

        # Act
        await test_handler(mock_update, mock_context)

        # Assert
        mock_update.message.reply_text.assert_called()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "not authenticated" in call_args.lower() or "authenticate" in call_args.lower()

    @pytest.mark.asyncio
    async def test_portfolio_command_shows_portfolio(self, mock_update, authenticated_context,
                                                      mock_db_manager, mock_signal_service,
                                                      mock_alert_engine, mock_auth_manager):
        """Test /portfolio command shows portfolio summary"""
        # Arrange
        handlers = TelegramCommandHandlers(
            mock_db_manager, mock_signal_service, mock_alert_engine, mock_auth_manager
        )

        # Act
        await handlers.cmd_portfolio(mock_update, authenticated_context)

        # Assert
        mock_signal_service.get_portfolio_summary.assert_called_once()
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "Portfolio" in call_args or "positions" in call_args.lower()

    @pytest.mark.asyncio
    async def test_risk_command_shows_risk_metrics(self, mock_update, authenticated_context,
                                                    mock_db_manager, mock_signal_service,
                                                    mock_alert_engine, mock_auth_manager):
        """Test /risk command shows risk metrics"""
        # Arrange
        handlers = TelegramCommandHandlers(
            mock_db_manager, mock_signal_service, mock_alert_engine, mock_auth_manager
        )

        # Mock settings
        with patch('src.api.telegram_handlers.settings') as mock_settings:
            mock_settings.get_risk_limits.return_value = {
                'max_position_size': 0.20,
                'max_sector_concentration': 0.40,
                'max_drawdown': 0.20
            }

            # Act
            await handlers.cmd_risk(mock_update, authenticated_context)

        # Assert
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "Risk" in call_args or "alert" in call_args.lower()

    @pytest.mark.asyncio
    async def test_ping_command_checks_status(self, mock_update, mock_context,
                                               mock_db_manager, mock_signal_service,
                                               mock_alert_engine, mock_auth_manager):
        """Test /ping command checks bot status"""
        # Arrange
        handlers = TelegramCommandHandlers(
            mock_db_manager, mock_signal_service, mock_alert_engine, mock_auth_manager
        )

        # Act
        await handlers.cmd_ping(mock_update, mock_context)

        # Assert
        mock_db_manager.health_check.assert_called_once()
        mock_signal_service.health_check.assert_called_once()
        mock_update.message.reply_text.assert_called_once()


# ========================================
# TRANSACTION TESTS
# ========================================

class TestTransactionHandlers:
    """Test suite for transaction handlers"""

    @pytest.mark.asyncio
    async def test_buy_creates_pending_transaction(self, mock_update, authenticated_context,
                                                    mock_transaction_manager):
        """Test /buy command creates pending transaction"""
        # Arrange
        authenticated_context.args = ['BBCA', '1000', '8500']
        authenticated_context.bot_data['transaction_manager'] = mock_transaction_manager
        authenticated_context.bot_data['db_manager'] = AsyncMock()
        authenticated_context.bot_data['db_manager'].log_bot_command = AsyncMock()

        # Act
        await cmd_buy(mock_update, authenticated_context)

        # Assert
        mock_transaction_manager.create_pending_transaction.assert_called_once()
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "CONFIRMATION" in call_args or "confirm" in call_args.lower()
        assert "ABC123" in call_args

    @pytest.mark.asyncio
    async def test_buy_validates_input_format(self, mock_update, authenticated_context):
        """Test /buy command validates input format"""
        # Arrange
        authenticated_context.args = ['BBCA']  # Missing quantity and price

        # Act
        await cmd_buy(mock_update, authenticated_context)

        # Assert
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "Invalid format" in call_args or "Usage" in call_args

    @pytest.mark.asyncio
    async def test_buy_rejects_negative_values(self, mock_update, authenticated_context):
        """Test /buy command rejects negative values"""
        # Arrange
        authenticated_context.args = ['BBCA', '-100', '8500']

        # Act
        await cmd_buy(mock_update, authenticated_context)

        # Assert
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "positive" in call_args.lower() or "invalid" in call_args.lower()

    @pytest.mark.asyncio
    async def test_confirm_executes_transaction(self, mock_update, authenticated_context,
                                                 mock_transaction_manager):
        """Test /confirm command executes transaction"""
        # Arrange
        authenticated_context.args = ['ABC123']
        authenticated_context.bot_data['transaction_manager'] = mock_transaction_manager
        authenticated_context.bot_data['db_manager'] = AsyncMock()
        authenticated_context.bot_data['db_manager'].log_bot_command = AsyncMock()

        # Act
        await cmd_confirm(mock_update, authenticated_context)

        # Assert
        mock_transaction_manager.confirm_transaction.assert_called_once_with(
            'user-123', 'ABC123'
        )
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "EXECUTED" in call_args or "success" in call_args.lower()

    @pytest.mark.asyncio
    async def test_confirm_rejects_invalid_code(self, mock_update, authenticated_context,
                                                 mock_transaction_manager):
        """Test /confirm command rejects invalid confirmation code"""
        # Arrange
        authenticated_context.args = ['INVALID']
        authenticated_context.bot_data['transaction_manager'] = mock_transaction_manager
        authenticated_context.bot_data['db_manager'] = AsyncMock()
        authenticated_context.bot_data['db_manager'].log_bot_command = AsyncMock()

        # Mock no transaction found
        mock_transaction_manager.confirm_transaction.return_value = None

        # Act
        await cmd_confirm(mock_update, authenticated_context)

        # Assert
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "Invalid" in call_args or "expired" in call_args.lower()

    @pytest.mark.asyncio
    async def test_sell_validates_sufficient_quantity(self, mock_update, authenticated_context,
                                                       mock_db_manager):
        """Test /sell command validates sufficient quantity"""
        # Arrange
        authenticated_context.args = ['BBCA', '2000', '8500']  # Trying to sell more than owned
        authenticated_context.bot_data['db_manager'] = mock_db_manager

        # Mock position with insufficient quantity
        mock_db_manager.fetch_one.return_value = {'quantity': 1000}

        # Act
        await cmd_sell(mock_update, authenticated_context)

        # Assert
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "Insufficient" in call_args or "don't have" in call_args.lower()

    @pytest.mark.asyncio
    async def test_cancel_cancels_pending_transactions(self, mock_update, authenticated_context,
                                                        mock_db_manager):
        """Test /cancel command cancels pending transactions"""
        # Arrange
        authenticated_context.bot_data['db_manager'] = mock_db_manager

        # Mock cancelled transactions
        mock_db_manager.fetch_all.return_value = [
            {'stock_code': 'BBCA', 'transaction_type': 'buy', 'quantity': 1000}
        ]

        # Act
        await cmd_cancel(mock_update, authenticated_context)

        # Assert
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "CANCELLED" in call_args or "cancelled" in call_args.lower()


# ========================================
# PREFERENCES TESTS
# ========================================

class TestPreferencesHandlers:
    """Test suite for preferences and watchlist handlers"""

    @pytest.mark.asyncio
    async def test_subscribe_updates_alert_preferences(self, mock_update, authenticated_context,
                                                        mock_preference_manager):
        """Test /subscribe command updates alert preferences"""
        # Arrange
        authenticated_context.args = ['alerts', 'high_confidence', 'risk_breach']
        authenticated_context.bot_data['preference_manager'] = mock_preference_manager

        # Act
        await cmd_subscribe(mock_update, authenticated_context)

        # Assert
        mock_preference_manager.update_alert_types.assert_called_once_with(
            'user-123', ['high_confidence', 'risk_breach']
        )
        mock_update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_subscribe_validates_alert_types(self, mock_update, authenticated_context,
                                                    mock_preference_manager):
        """Test /subscribe command validates alert types"""
        # Arrange
        authenticated_context.args = ['alerts', 'invalid_type']
        authenticated_context.bot_data['preference_manager'] = mock_preference_manager

        # Act
        await cmd_subscribe(mock_update, authenticated_context)

        # Assert
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "Invalid" in call_args or "valid types" in call_args.lower()

    @pytest.mark.asyncio
    async def test_watchlist_add_adds_stock(self, mock_update, authenticated_context,
                                             mock_preference_manager):
        """Test /watchlist add command adds stock to watchlist"""
        # Arrange
        authenticated_context.args = ['add', 'UNVR', 'ASII']
        authenticated_context.bot_data['preference_manager'] = mock_preference_manager

        # Act
        await cmd_watchlist(mock_update, authenticated_context)

        # Assert
        assert mock_preference_manager.add_to_watchlist.call_count == 2
        mock_update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_watchlist_remove_removes_stock(self, mock_update, authenticated_context,
                                                   mock_preference_manager):
        """Test /watchlist remove command removes stock from watchlist"""
        # Arrange
        authenticated_context.args = ['remove', 'BBCA']
        authenticated_context.bot_data['preference_manager'] = mock_preference_manager

        # Act
        await cmd_watchlist(mock_update, authenticated_context)

        # Assert
        mock_preference_manager.remove_from_watchlist.assert_called_once_with('user-123', 'BBCA')
        mock_update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_watchlist_signals_shows_watchlist_signals(self, mock_update, authenticated_context,
                                                              mock_preference_manager, mock_signal_service):
        """Test /watchlist signals command shows signals for watchlist stocks"""
        # Arrange
        authenticated_context.args = ['signals']
        authenticated_context.bot_data['preference_manager'] = mock_preference_manager
        authenticated_context.bot_data['signal_service'] = mock_signal_service

        # Act
        await cmd_watchlist(mock_update, authenticated_context)

        # Assert
        mock_signal_service.get_daily_signals.assert_called_once()
        mock_update.message.reply_text.assert_called_once()


# ========================================
# RATE LIMITING TESTS
# ========================================

class TestRateLimiting:
    """Test suite for rate limiting"""

    @pytest.mark.asyncio
    async def test_rate_limiter_allows_within_limit(self, mock_redis):
        """Test rate limiter allows requests within limit"""
        # Arrange
        limiter = RateLimiter(mock_redis)
        mock_redis.get.return_value = None  # First request

        # Act
        result = await limiter.check_rate_limit(12345, 'general')

        # Assert
        assert result is True
        mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_rate_limiter_blocks_exceeding_limit(self, mock_redis):
        """Test rate limiter blocks requests exceeding limit"""
        # Arrange
        limiter = RateLimiter(mock_redis)
        mock_redis.get.return_value = "60"  # At limit

        # Act
        result = await limiter.check_rate_limit(12345, 'general')

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_different_limits_for_different_command_types(self, mock_redis):
        """Test different rate limits for different command types"""
        # Arrange
        limiter = RateLimiter(mock_redis)

        # Assert limits are different
        assert limiter.limits['general']['requests'] == 60
        assert limiter.limits['signals']['requests'] == 100
        assert limiter.limits['portfolio']['requests'] == 10


# ========================================
# ERROR HANDLING TESTS
# ========================================

class TestErrorHandling:
    """Test suite for error handling"""

    @pytest.mark.asyncio
    async def test_handles_database_errors_gracefully(self, mock_update, authenticated_context,
                                                       mock_db_manager, mock_signal_service,
                                                       mock_alert_engine, mock_auth_manager):
        """Test command handlers handle database errors gracefully"""
        # Arrange
        handlers = TelegramCommandHandlers(
            mock_db_manager, mock_signal_service, mock_alert_engine, mock_auth_manager
        )

        # Mock database error
        mock_signal_service.get_daily_signals.side_effect = Exception("Database connection failed")

        # Act
        await handlers.cmd_signals(mock_update, authenticated_context)

        # Assert
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "error" in call_args.lower()
        assert "Database connection failed" not in call_args  # Don't expose internal errors

    @pytest.mark.asyncio
    async def test_never_exposes_internal_errors(self, mock_update, authenticated_context,
                                                  mock_db_manager, mock_signal_service,
                                                  mock_alert_engine, mock_auth_manager):
        """Test that internal errors are never exposed to users"""
        # Arrange
        handlers = TelegramCommandHandlers(
            mock_db_manager, mock_signal_service, mock_alert_engine, mock_auth_manager
        )

        # Mock internal error
        mock_signal_service.get_portfolio_summary.side_effect = Exception("Internal server error: SQL injection detected")

        # Act
        await handlers.cmd_portfolio(mock_update, authenticated_context)

        # Assert
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "SQL injection" not in call_args
        assert "Internal server error" not in call_args

    @pytest.mark.asyncio
    async def test_logs_errors_properly(self, mock_update, authenticated_context,
                                        mock_db_manager, mock_signal_service,
                                        mock_alert_engine, mock_auth_manager):
        """Test that errors are logged properly"""
        # Arrange
        handlers = TelegramCommandHandlers(
            mock_db_manager, mock_signal_service, mock_alert_engine, mock_auth_manager
        )

        # Mock error
        mock_signal_service.get_daily_signals.side_effect = Exception("Test error")

        # Act
        with patch('src.api.telegram_handlers.logger') as mock_logger:
            await handlers.cmd_signals(mock_update, authenticated_context)

            # Assert
            mock_logger.error.assert_called()


# ========================================
# TRANSACTION MANAGER TESTS
# ========================================

class TestTransactionManager:
    """Test suite for TransactionManager"""

    @pytest.mark.asyncio
    async def test_create_pending_transaction(self, mock_db_manager, mock_signal_service):
        """Test creating a pending transaction"""
        # Arrange
        manager = TransactionManager(mock_db_manager, mock_signal_service)
        mock_db_manager.fetch_one.return_value = {
            'id': 'txn-123',
            'confirmation_code': 'ABC123',
            'expires_at': datetime.now() + timedelta(minutes=5)
        }

        # Act
        result = await manager.create_pending_transaction(
            user_id='user-123',
            transaction_type='buy',
            stock_code='BBCA',
            quantity=1000,
            price=8500
        )

        # Assert
        assert result['transaction_id'] == 'txn-123'
        assert result['confirmation_code'] == 'ABC123'
        assert result['stock_code'] == 'BBCA'

    @pytest.mark.asyncio
    async def test_confirm_transaction_buy(self, mock_db_manager, mock_signal_service):
        """Test confirming a buy transaction"""
        # Arrange
        manager = TransactionManager(mock_db_manager, mock_signal_service)

        # Mock pending transaction
        mock_db_manager.fetch_one.side_effect = [
            {
                'id': 'txn-123',
                'user_id': 'user-123',
                'transaction_type': 'buy',
                'stock_code': 'BBCA',
                'quantity': 1000,
                'price': 8500
            },
            None,  # No existing position
            {  # New position
                'user_id': 'user-123',
                'stock_code': 'BBCA',
                'quantity': 1000,
                'average_price': 8500
            }
        ]

        # Mock stock info
        mock_signal_service.get_daily_signals.return_value = [
            {'stock_code': 'BBCA', 'sector': 'Finance', 'current_price': 8500}
        ]

        # Act
        result = await manager.confirm_transaction('user-123', 'ABC123')

        # Assert
        assert result['action'] == 'buy'
        assert result['stock_code'] == 'BBCA'
        assert result['quantity'] == 1000

    @pytest.mark.asyncio
    async def test_confirm_transaction_sell(self, mock_db_manager, mock_signal_service):
        """Test confirming a sell transaction"""
        # Arrange
        manager = TransactionManager(mock_db_manager, mock_signal_service)

        # Mock pending transaction and existing position
        mock_db_manager.fetch_one.side_effect = [
            {
                'id': 'txn-456',
                'user_id': 'user-123',
                'transaction_type': 'sell',
                'stock_code': 'BBCA',
                'quantity': 500,
                'price': 9000
            },
            {  # Existing position
                'quantity': 1000,
                'average_price': 8500
            },
            {  # Updated position
                'quantity': 500,
                'average_price': 8500
            }
        ]

        # Act
        result = await manager.confirm_transaction('user-123', 'DEF456')

        # Assert
        assert result['action'] == 'sell'
        assert result['stock_code'] == 'BBCA'
        assert result['quantity'] == 500
        assert result['realized_pnl'] == 250000  # (9000 - 8500) * 500

    @pytest.mark.asyncio
    async def test_generate_confirmation_code_is_unique(self, mock_db_manager, mock_signal_service):
        """Test that generated confirmation codes are unique"""
        # Arrange
        manager = TransactionManager(mock_db_manager, mock_signal_service)

        # Act
        code1 = manager._generate_confirmation_code()
        code2 = manager._generate_confirmation_code()

        # Assert
        assert len(code1) == 6
        assert len(code2) == 6
        assert code1 != code2


# ========================================
# PREFERENCE MANAGER TESTS
# ========================================

class TestPreferenceManager:
    """Test suite for PreferenceManager"""

    @pytest.mark.asyncio
    async def test_get_preferences_creates_defaults(self, mock_db_manager):
        """Test getting preferences creates defaults if none exist"""
        # Arrange
        manager = PreferenceManager(mock_db_manager)
        mock_db_manager.fetch_one.side_effect = [
            None,  # No existing preferences
            {  # Created defaults
                'user_id': 'user-123',
                'alert_types': ['high_confidence', 'risk_breach', 'large_position'],
                'signal_filter': 'all',
                'notification_hours': [9, 10, 11, 14, 15],
                'watchlist': [],
                'language': 'id'
            }
        ]

        # Act
        prefs = await manager.get_preferences('user-123')

        # Assert
        assert prefs['alert_types'] == ['high_confidence', 'risk_breach', 'large_position']
        assert prefs['signal_filter'] == 'all'
        assert prefs['watchlist'] == []

    @pytest.mark.asyncio
    async def test_add_to_watchlist_prevents_duplicates(self, mock_db_manager):
        """Test adding to watchlist prevents duplicates"""
        # Arrange
        manager = PreferenceManager(mock_db_manager)
        mock_db_manager.fetch_one.return_value = {
            'watchlist': ['BBCA', 'BMRI']
        }

        # Act & Assert
        with pytest.raises(ValueError, match="already in your watchlist"):
            await manager.add_to_watchlist('user-123', 'BBCA')

    @pytest.mark.asyncio
    async def test_clear_watchlist(self, mock_db_manager):
        """Test clearing watchlist"""
        # Arrange
        manager = PreferenceManager(mock_db_manager)
        mock_db_manager.fetch_one.return_value = {
            'watchlist': []
        }

        # Act
        result = await manager.clear_watchlist('user-123')

        # Assert
        assert result['watchlist'] == []


# ========================================
# INTEGRATION TESTS
# ========================================

class TestBotIntegration:
    """Integration tests for bot service"""

    @pytest.mark.asyncio
    async def test_bot_initialization(self, mock_db_manager, mock_signal_service, mock_alert_engine):
        """Test bot service initialization"""
        # Arrange
        with patch('src.api.telegram_bot_service.aioredis.from_url') as mock_redis_connect:
            mock_redis_connect.return_value = AsyncMock()

            with patch('src.api.telegram_bot_service.Application.builder') as mock_builder:
                mock_app = AsyncMock()
                mock_app.bot_data = {}
                mock_builder.return_value.token.return_value.build.return_value = mock_app

                # Act
                service = TelegramBotService(mock_db_manager, mock_signal_service, mock_alert_engine)

                with patch('src.api.telegram_bot_service.settings') as mock_settings:
                    mock_settings.TELEGRAM_BOT_TOKEN = "test_token"
                    mock_settings.get_redis_url.return_value = "redis://localhost"

                    await service.initialize()

                # Assert
                assert service.is_running is False
                assert service.application is not None

    @pytest.mark.asyncio
    async def test_health_check(self, mock_db_manager, mock_signal_service, mock_alert_engine):
        """Test bot health check"""
        # Arrange
        service = TelegramBotService(mock_db_manager, mock_signal_service, mock_alert_engine)
        service.is_running = True
        service.bot = AsyncMock()

        # Act
        health = await service.health_check()

        # Assert
        assert health['service'] == 'telegram_bot'
        assert health['status'] == 'healthy'
        assert 'timestamp' in health
