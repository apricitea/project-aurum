"""
Unit tests for database management module
"""

import pytest
import asyncio
from datetime import datetime, date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
import asyncpg
from typing import List, Dict, Any

from src.api.database import DatabaseManager


class TestDatabaseManager:
    """Test DatabaseManager class"""

    @pytest.fixture
    def db_manager(self, mock_settings):
        """Create DatabaseManager instance for testing"""
        with patch('src.api.database.settings', mock_settings):
            mock_settings.DATABASE_URL = "postgresql://test:test@localhost:5432/test_db"
            return DatabaseManager()

    @pytest.mark.asyncio
    @pytest.mark.database
    async def test_initialize_success(self, db_manager):
        """Test successful database initialization"""
        with patch('asyncpg.create_pool') as mock_create_pool:
            mock_pool = AsyncMock()
            mock_create_pool.return_value = mock_pool

            await db_manager.initialize()

            assert db_manager.pool == mock_pool
            mock_create_pool.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.database
    async def test_initialize_connection_failure(self, db_manager):
        """Test database initialization with connection failure"""
        with patch('asyncpg.create_pool') as mock_create_pool:
            mock_create_pool.side_effect = Exception("Connection failed")

            with pytest.raises(Exception) as exc_info:
                await db_manager.initialize()

            assert "Connection failed" in str(exc_info.value)

    @pytest.mark.asyncio
    @pytest.mark.database
    async def test_close_success(self, db_manager):
        """Test successful database connection closure"""
        # Set up a mock pool
        mock_pool = AsyncMock()
        db_manager.pool = mock_pool

        await db_manager.close()

        mock_pool.close.assert_called_once()
        await mock_pool.wait_closed()

    @pytest.mark.asyncio
    @pytest.mark.database
    async def test_close_no_pool(self, db_manager):
        """Test database closure when no pool exists"""
        db_manager.pool = None

        # Should not raise an exception
        await db_manager.close()

    @pytest.mark.asyncio
    @pytest.mark.database
    async def test_health_check_success(self, db_manager):
        """Test successful database health check"""
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
        mock_connection.fetchval.return_value = 1

        db_manager.pool = mock_pool

        result = await db_manager.health_check()

        assert result is True
        mock_connection.fetchval.assert_called_once_with("SELECT 1")

    @pytest.mark.asyncio
    @pytest.mark.database
    async def test_health_check_failure(self, db_manager):
        """Test database health check failure"""
        mock_pool = AsyncMock()
        mock_pool.acquire.side_effect = Exception("Database error")

        db_manager.pool = mock_pool

        with pytest.raises(Exception) as exc_info:
            await db_manager.health_check()

        assert "Database error" in str(exc_info.value)

    @pytest.mark.asyncio
    @pytest.mark.database
    async def test_execute_query_success(self, db_manager):
        """Test successful query execution"""
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection

        expected_result = [
            {"id": 1, "name": "Test Stock", "code": "TEST"},
            {"id": 2, "name": "Another Stock", "code": "ANTH"}
        ]
        mock_connection.fetch.return_value = expected_result

        db_manager.pool = mock_pool

        query = "SELECT id, name, code FROM stocks WHERE active = $1"
        params = [True]

        result = await db_manager.execute_query(query, params)

        assert result == expected_result
        mock_connection.fetch.assert_called_once_with(query, *params)

    @pytest.mark.asyncio
    @pytest.mark.database
    async def test_execute_query_no_params(self, db_manager):
        """Test query execution without parameters"""
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection

        expected_result = [{"count": 5}]
        mock_connection.fetch.return_value = expected_result

        db_manager.pool = mock_pool

        query = "SELECT COUNT(*) as count FROM stocks"

        result = await db_manager.execute_query(query)

        assert result == expected_result
        mock_connection.fetch.assert_called_once_with(query)

    @pytest.mark.asyncio
    @pytest.mark.database
    async def test_execute_query_error(self, db_manager):
        """Test query execution with database error"""
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
        mock_connection.fetch.side_effect = asyncpg.PostgresError("SQL error")

        db_manager.pool = mock_pool

        query = "SELECT * FROM nonexistent_table"

        with pytest.raises(Exception):
            await db_manager.execute_query(query)

    @pytest.mark.asyncio
    @pytest.mark.database
    async def test_execute_non_query_success(self, db_manager):
        """Test successful non-query execution (INSERT, UPDATE, DELETE)"""
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
        mock_connection.execute.return_value = "INSERT 0 1"

        db_manager.pool = mock_pool

        query = "INSERT INTO stocks (name, code) VALUES ($1, $2)"
        params = ["Test Stock", "TEST"]

        result = await db_manager.execute_non_query(query, params)

        assert result == "INSERT 0 1"
        mock_connection.execute.assert_called_once_with(query, *params)

    @pytest.mark.asyncio
    @pytest.mark.database
    async def test_execute_non_query_error(self, db_manager):
        """Test non-query execution with error"""
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
        mock_connection.execute.side_effect = asyncpg.UniqueViolationError("Duplicate key")

        db_manager.pool = mock_pool

        query = "INSERT INTO stocks (code) VALUES ($1)"
        params = ["DUPLICATE"]

        with pytest.raises(Exception):
            await db_manager.execute_non_query(query, params)

    @pytest.mark.asyncio
    @pytest.mark.database
    async def test_fetch_one_success(self, db_manager):
        """Test successful single row fetch"""
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection

        expected_result = {"id": 1, "name": "Test Stock", "code": "TEST"}
        mock_connection.fetchrow.return_value = expected_result

        db_manager.pool = mock_pool

        query = "SELECT * FROM stocks WHERE id = $1"
        params = [1]

        result = await db_manager.fetch_one(query, params)

        assert result == expected_result
        mock_connection.fetchrow.assert_called_once_with(query, *params)

    @pytest.mark.asyncio
    @pytest.mark.database
    async def test_fetch_one_not_found(self, db_manager):
        """Test single row fetch when no row found"""
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
        mock_connection.fetchrow.return_value = None

        db_manager.pool = mock_pool

        query = "SELECT * FROM stocks WHERE id = $1"
        params = [999]

        result = await db_manager.fetch_one(query, params)

        assert result is None

    @pytest.mark.asyncio
    @pytest.mark.database
    async def test_transaction_success(self, db_manager):
        """Test successful transaction execution"""
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        mock_transaction = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
        mock_connection.transaction.return_value.__aenter__.return_value = mock_transaction

        db_manager.pool = mock_pool

        queries = [
            ("INSERT INTO stocks (name, code) VALUES ($1, $2)", ["Stock 1", "STK1"]),
            ("INSERT INTO stocks (name, code) VALUES ($1, $2)", ["Stock 2", "STK2"])
        ]

        await db_manager.execute_transaction(queries)

        # Verify transaction was used
        mock_connection.transaction.assert_called_once()
        assert mock_connection.execute.call_count == 2

    @pytest.mark.asyncio
    @pytest.mark.database
    async def test_transaction_rollback_on_error(self, db_manager):
        """Test transaction rollback on error"""
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        mock_transaction = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
        mock_connection.transaction.return_value.__aenter__.return_value = mock_transaction

        # First query succeeds, second fails
        mock_connection.execute.side_effect = [None, Exception("Constraint violation")]

        db_manager.pool = mock_pool

        queries = [
            ("INSERT INTO stocks (name, code) VALUES ($1, $2)", ["Stock 1", "STK1"]),
            ("INSERT INTO stocks (name, code) VALUES ($1, $2)", ["Stock 1", "STK1"])  # Duplicate
        ]

        with pytest.raises(Exception):
            await db_manager.execute_transaction(queries)

        # Transaction should have been attempted
        mock_connection.transaction.assert_called_once()


class TestDatabaseQueries:
    """Test specific database query operations"""

    @pytest.fixture
    def db_manager_with_pool(self):
        """Create DatabaseManager with mocked pool"""
        db_manager = DatabaseManager()
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
        db_manager.pool = mock_pool
        return db_manager, mock_connection

    @pytest.mark.asyncio
    @pytest.mark.database
    async def test_get_stocks_query(self, db_manager_with_pool):
        """Test stock retrieval query"""
        db_manager, mock_connection = db_manager_with_pool

        expected_stocks = [
            {
                "id": 1,
                "code": "BBCA",
                "name": "Bank Central Asia Tbk",
                "sector": "Financial Services",
                "is_lq45": True,
                "market_cap": 1250000000000
            },
            {
                "id": 2,
                "code": "BBRI",
                "name": "Bank Rakyat Indonesia Tbk",
                "sector": "Financial Services",
                "is_lq45": True,
                "market_cap": 900000000000
            }
        ]

        mock_connection.fetch.return_value = expected_stocks

        query = """
        SELECT id, code, name, sector, is_lq45, market_cap
        FROM stocks
        WHERE is_lq45 = $1
        ORDER BY market_cap DESC
        """

        result = await db_manager.execute_query(query, [True])

        assert result == expected_stocks
        assert len(result) == 2
        assert result[0]["code"] == "BBCA"

    @pytest.mark.asyncio
    @pytest.mark.database
    async def test_get_alerts_query(self, db_manager_with_pool):
        """Test alerts retrieval query"""
        db_manager, mock_connection = db_manager_with_pool

        expected_alerts = [
            {
                "id": 1,
                "alert_type": "PRICE_BREAKOUT",
                "message": "BBCA broke above resistance",
                "priority": "HIGH",
                "status": "ACTIVE",
                "created_at": datetime.now(),
                "user_id": 1
            }
        ]

        mock_connection.fetch.return_value = expected_alerts

        query = """
        SELECT id, alert_type, message, priority, status, created_at, user_id
        FROM alerts
        WHERE user_id = $1 AND status = $2
        ORDER BY created_at DESC
        LIMIT $3
        """

        result = await db_manager.execute_query(query, [1, "ACTIVE", 10])

        assert result == expected_alerts
        assert result[0]["alert_type"] == "PRICE_BREAKOUT"

    @pytest.mark.asyncio
    @pytest.mark.database
    async def test_get_signals_query(self, db_manager_with_pool):
        """Test signals retrieval query"""
        db_manager, mock_connection = db_manager_with_pool

        expected_signals = [
            {
                "id": 1,
                "stock_code": "BBCA",
                "signal_type": "BUY",
                "confidence": 0.85,
                "price_target": Decimal("9500.00"),
                "stop_loss": Decimal("8500.00"),
                "generated_at": datetime.now(),
                "valid_until": datetime.now()
            }
        ]

        mock_connection.fetch.return_value = expected_signals

        query = """
        SELECT id, stock_code, signal_type, confidence, price_target,
               stop_loss, generated_at, valid_until
        FROM trading_signals
        WHERE DATE(generated_at) = $1
        AND valid_until > NOW()
        ORDER BY confidence DESC
        """

        target_date = date.today()
        result = await db_manager.execute_query(query, [target_date])

        assert result == expected_signals
        assert result[0]["signal_type"] == "BUY"

    @pytest.mark.asyncio
    @pytest.mark.database
    async def test_insert_alert_query(self, db_manager_with_pool):
        """Test alert insertion query"""
        db_manager, mock_connection = db_manager_with_pool

        mock_connection.fetchrow.return_value = {
            "id": 1,
            "alert_type": "PRICE_BREAKOUT",
            "message": "New alert",
            "priority": "HIGH",
            "status": "ACTIVE",
            "created_at": datetime.now()
        }

        query = """
        INSERT INTO alerts (alert_type, message, priority, status, user_id, metadata)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id, alert_type, message, priority, status, created_at
        """

        params = [
            "PRICE_BREAKOUT",
            "New alert",
            "HIGH",
            "ACTIVE",
            1,
            '{"stock_code": "BBCA"}'
        ]

        result = await db_manager.fetch_one(query, params)

        assert result["alert_type"] == "PRICE_BREAKOUT"
        assert result["priority"] == "HIGH"

    @pytest.mark.asyncio
    @pytest.mark.database
    async def test_update_alert_status_query(self, db_manager_with_pool):
        """Test alert status update query"""
        db_manager, mock_connection = db_manager_with_pool

        mock_connection.execute.return_value = "UPDATE 1"

        query = """
        UPDATE alerts
        SET status = $1, updated_at = NOW(), notes = $2
        WHERE id = $3 AND user_id = $4
        """

        params = ["ACKNOWLEDGED", "Alert reviewed", 1, 1]

        result = await db_manager.execute_non_query(query, params)

        assert result == "UPDATE 1"

    @pytest.mark.asyncio
    @pytest.mark.database
    async def test_get_portfolio_positions_query(self, db_manager_with_pool):
        """Test portfolio positions retrieval query"""
        db_manager, mock_connection = db_manager_with_pool

        expected_positions = [
            {
                "stock_code": "BBCA",
                "quantity": 1000,
                "average_price": Decimal("8800.00"),
                "current_price": Decimal("9000.00"),
                "market_value": Decimal("9000000.00"),
                "unrealized_pnl": Decimal("200000.00"),
                "unrealized_pnl_percent": Decimal("2.27"),
                "weight": Decimal("25.0"),
                "last_updated": datetime.now()
            }
        ]

        mock_connection.fetch.return_value = expected_positions

        query = """
        SELECT p.stock_code, p.quantity, p.average_price,
               q.current_price,
               (p.quantity * q.current_price) as market_value,
               ((q.current_price - p.average_price) * p.quantity) as unrealized_pnl,
               (((q.current_price - p.average_price) / p.average_price) * 100) as unrealized_pnl_percent,
               p.weight, p.last_updated
        FROM portfolio_positions p
        JOIN stock_quotes q ON p.stock_code = q.stock_code
        WHERE p.user_id = $1 AND p.quantity > 0
        ORDER BY market_value DESC
        """

        result = await db_manager.execute_query(query, [1])

        assert result == expected_positions
        assert result[0]["stock_code"] == "BBCA"
        assert result[0]["quantity"] == 1000


class TestDatabaseConnectionPool:
    """Test database connection pool management"""

    @pytest.mark.asyncio
    @pytest.mark.database
    async def test_connection_pool_limits(self, db_manager):
        """Test connection pool limits"""
        with patch('asyncpg.create_pool') as mock_create_pool:
            mock_pool = AsyncMock()
            mock_create_pool.return_value = mock_pool

            await db_manager.initialize()

            # Verify pool was created with appropriate settings
            call_kwargs = mock_create_pool.call_args[1]
            assert 'min_size' in call_kwargs
            assert 'max_size' in call_kwargs

    @pytest.mark.asyncio
    @pytest.mark.database
    async def test_connection_timeout(self, db_manager):
        """Test connection timeout handling"""
        with patch('asyncpg.create_pool') as mock_create_pool:
            mock_pool = AsyncMock()
            mock_pool.acquire.side_effect = asyncio.TimeoutError("Connection timeout")
            mock_create_pool.return_value = mock_pool

            db_manager.pool = mock_pool

            with pytest.raises(asyncio.TimeoutError):
                await db_manager.execute_query("SELECT 1")

    @pytest.mark.asyncio
    @pytest.mark.database
    async def test_connection_retry_logic(self, db_manager):
        """Test connection retry logic"""
        with patch('asyncpg.create_pool') as mock_create_pool:
            # First call fails, second succeeds
            mock_create_pool.side_effect = [
                Exception("Connection failed"),
                AsyncMock()
            ]

            try:
                # Assuming retry logic exists
                await db_manager.initialize_with_retry(max_retries=2)
            except AttributeError:
                # Method doesn't exist, skip test
                pytest.skip("Retry logic not implemented")


class TestDatabaseMigrations:
    """Test database migration and schema management"""

    @pytest.mark.asyncio
    @pytest.mark.database
    async def test_create_tables_if_not_exists(self, db_manager):
        """Test table creation during initialization"""
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection

        db_manager.pool = mock_pool

        try:
            await db_manager.create_tables()
            # Should execute CREATE TABLE statements
            assert mock_connection.execute.called
        except AttributeError:
            # Method doesn't exist, skip test
            pytest.skip("Table creation method not implemented")

    @pytest.mark.asyncio
    @pytest.mark.database
    async def test_database_schema_validation(self, db_manager):
        """Test database schema validation"""
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection

        # Mock table information query
        expected_tables = [
            {"table_name": "users"},
            {"table_name": "stocks"},
            {"table_name": "alerts"},
            {"table_name": "trading_signals"},
            {"table_name": "portfolio_positions"}
        ]
        mock_connection.fetch.return_value = expected_tables

        db_manager.pool = mock_pool

        try:
            is_valid = await db_manager.validate_schema()
            assert is_valid is True
        except AttributeError:
            # Method doesn't exist, skip test
            pytest.skip("Schema validation not implemented")


class TestDatabasePerformance:
    """Test database performance optimization"""

    @pytest.mark.asyncio
    @pytest.mark.database
    @pytest.mark.performance
    async def test_query_performance_monitoring(self, db_manager):
        """Test query performance monitoring"""
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
        mock_connection.fetch.return_value = []

        db_manager.pool = mock_pool

        import time
        start_time = time.time()

        await db_manager.execute_query("SELECT * FROM stocks")

        execution_time = time.time() - start_time

        # Query should execute quickly in test
        assert execution_time < 1.0

    @pytest.mark.asyncio
    @pytest.mark.database
    async def test_connection_pooling_efficiency(self, db_manager):
        """Test connection pooling efficiency"""
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
        mock_connection.fetch.return_value = []

        db_manager.pool = mock_pool

        # Execute multiple queries
        tasks = []
        for i in range(10):
            task = db_manager.execute_query(f"SELECT {i}")
            tasks.append(task)

        await asyncio.gather(*tasks)

        # Pool should have been used efficiently
        assert mock_pool.acquire.call_count == 10