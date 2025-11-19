"""
Database management and models for Indonesian Quantitative Trading Alert System
Handles PostgreSQL and SQLite connections, schema management, and data access layer
"""

import asyncio
import asyncpg
from asyncpg import Pool
from typing import List, Dict, Optional, Any, Union
from datetime import datetime, timedelta
import logging
import json
from contextlib import asynccontextmanager
import os
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, DateTime, Float, Boolean, JSON, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB as PostgreSQL_JSONB
from sqlalchemy.types import TypeDecorator
import uuid
from .config import settings

# Create a cross-database JSONB type that works with both PostgreSQL and SQLite
class JSONB(TypeDecorator):
    """Platform-independent JSONB type. Uses JSONB for PostgreSQL, JSON for others."""
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PostgreSQL_JSONB())
        else:
            return dialect.type_descriptor(JSON())


# Create a cross-database UUID type
class GUID(TypeDecorator):
    """Platform-independent GUID type. Uses UUID for PostgreSQL, String for others."""
    impl = String(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            from sqlalchemy.dialects.postgresql import UUID as PostgreSQL_UUID
            return dialect.type_descriptor(PostgreSQL_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value) if not isinstance(value, uuid.UUID) else value
        else:
            return str(value) if not isinstance(value, str) else value

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                value = uuid.UUID(value)
            return value


from .config import settings

logger = logging.getLogger(__name__)

# SQLAlchemy Base
Base = declarative_base()


class User(Base):
    """User model for authentication and authorization"""
    __tablename__ = "users"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="trader")
    permissions = Column(JSONB, default={})
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)

    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission"""
        return self.permissions.get(permission, False) or self.role == "admin"


class Alert(Base):
    """Alert model for storing trading alerts"""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_type = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    priority = Column(String(10), nullable=False, default="medium")
    status = Column(String(20), nullable=False, default="active")
    meta_data = Column(JSONB, default={})
    stock_code = Column(String(10))
    user_id = Column(GUID, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    acknowledged_at = Column(DateTime)
    acknowledged_by = Column(GUID, ForeignKey("users.id"))
    expires_at = Column(DateTime)


class TradingSignal(Base):
    """Trading signal model"""
    __tablename__ = "trading_signals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False)
    stock_code = Column(String(10), nullable=False)
    sector = Column(String(50))
    signal_type = Column(String(20), nullable=False)  # BUY, SELL, HOLD, STRONG_BUY, STRONG_SELL
    composite_score = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    position_size = Column(Float, nullable=False)
    current_price = Column(Float, nullable=False)
    volume = Column(Float)
    technical_score = Column(Float)
    fundamental_score = Column(Float)
    sentiment_score = Column(Float)
    risk_adjusted = Column(Boolean, default=False)
    meta_data = Column(JSONB, default={})
    generated_at = Column(DateTime, default=datetime.utcnow)


class Portfolio(Base):
    """Portfolio position model"""
    __tablename__ = "portfolio"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(10), nullable=False)
    quantity = Column(Integer, nullable=False)
    average_price = Column(Float, nullable=False)
    current_price = Column(Float)
    sector = Column(String(50))
    market_value = Column(Float)
    unrealized_pnl = Column(Float)
    position_size_percent = Column(Float)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = Column(GUID, ForeignKey("users.id"))


class RiskAlert(Base):
    """Risk alert model"""
    __tablename__ = "risk_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_type = Column(String(50), nullable=False)
    severity = Column(String(10), nullable=False)
    message = Column(Text, nullable=False)
    stock_code = Column(String(10))
    sector = Column(String(50))
    threshold_value = Column(Float)
    current_value = Column(Float)
    is_active = Column(Boolean, default=True)
    meta_data = Column(JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime)


class MarketData(Base):
    """Market data model for real-time price tracking"""
    __tablename__ = "market_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(10), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    open_price = Column(Float)
    high_price = Column(Float)
    low_price = Column(Float)
    close_price = Column(Float)
    volume = Column(Float)
    trade_count = Column(Integer)
    vwap = Column(Float)
    bid_price = Column(Float)
    ask_price = Column(Float)
    bid_size = Column(Float)
    ask_size = Column(Float)


class SystemMetric(Base):
    """System performance metrics"""
    __tablename__ = "system_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    meta_data = Column(JSONB, default={})


class SignalGenerationTask(Base):
    """Signal generation task tracking"""
    __tablename__ = "signal_generation_tasks"

    id = Column(String(50), primary_key=True)  # UUID string
    status = Column(String(20), nullable=False, default="pending")
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    error_message = Column(Text)
    meta_data = Column(JSONB, default={})
    signals_generated = Column(Integer, default=0)


class DatabaseManager:
    """
    Database manager for handling PostgreSQL connections and operations
    Uses asyncpg for async operations and SQLAlchemy for ORM
    """

    def __init__(self):
        self.pool: Optional[Pool] = None
        self.engine = None
        self.session_factory = None
        self._connection_string = self._build_connection_string()

    def _build_connection_string(self) -> str:
        """Build database connection string"""
        # Use the database URL from settings if available
        return settings.get_database_url()

    async def initialize(self):
        """Initialize database connections and create tables"""
        try:
            # Check if using SQLite or PostgreSQL
            if self._connection_string.startswith("sqlite"):
                await self._initialize_sqlite()
            else:
                await self._initialize_postgresql()

            logger.info("Database initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            raise

    async def _initialize_sqlite(self):
        """Initialize SQLite database"""
        # SQLite doesn't need asyncpg, just use SQLAlchemy
        self.engine = create_engine(
            self._connection_string,
            echo=False,
            pool_pre_ping=True
        )

        self.session_factory = sessionmaker(bind=self.engine)

        # Create tables using SQLAlchemy
        Base.metadata.create_all(self.engine)

        # SQLite doesn't support asyncpg pool
        self.pool = None

    async def _initialize_postgresql(self):
        """Initialize PostgreSQL database"""
        # Create asyncpg connection pool
        self.pool = await asyncpg.create_pool(
            self._connection_string,
            min_size=5,
            max_size=20,
            command_timeout=60,
            server_settings={
                'jit': 'off',
                'application_name': 'trading_alert_system'
            }
        )

        # Create SQLAlchemy engine for ORM operations
        self.engine = create_engine(
            self._connection_string,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=3600
        )

        self.session_factory = sessionmaker(bind=self.engine)

        # Create tables
        await self.create_tables()

        # Create indexes for performance
        await self.create_indexes()

    async def create_tables(self):
        """Create database tables if they don't exist"""
        try:
            # Create tables using SQLAlchemy
            Base.metadata.create_all(self.engine)

            # Create additional indexes and constraints using raw SQL
            async with self.pool.acquire() as conn:
                # Create partitioned tables for time-series data
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS market_data_partitioned (
                        LIKE market_data INCLUDING ALL
                    ) PARTITION BY RANGE (timestamp);
                """)

                # Create monthly partitions for current and next month
                current_month = datetime.now().replace(day=1)
                next_month = (current_month + timedelta(days=32)).replace(day=1)

                partition_name = f"market_data_{current_month.strftime('%Y_%m')}"
                await conn.execute(f"""
                    CREATE TABLE IF NOT EXISTS {partition_name}
                    PARTITION OF market_data_partitioned
                    FOR VALUES FROM ('{current_month}') TO ('{next_month}');
                """)

            logger.info("Database tables created successfully")

        except Exception as e:
            logger.error(f"Failed to create tables: {str(e)}")
            raise

    async def create_indexes(self):
        """Create performance indexes"""
        try:
            async with self.pool.acquire() as conn:
                # Alert indexes
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_alerts_status_created
                    ON alerts(status, created_at DESC);
                """)

                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_alerts_user_type
                    ON alerts(user_id, alert_type);
                """)

                # Trading signal indexes
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_signals_date_stock
                    ON trading_signals(date DESC, stock_code);
                """)

                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_signals_type_confidence
                    ON trading_signals(signal_type, confidence DESC);
                """)

                # Portfolio indexes
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_portfolio_user_stock
                    ON portfolio(user_id, stock_code);
                """)

                # Market data indexes
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_market_data_stock_time
                    ON market_data(stock_code, timestamp DESC);
                """)

                # Risk alert indexes
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_risk_alerts_active_type
                    ON risk_alerts(is_active, alert_type, created_at DESC);
                """)

            logger.info("Database indexes created successfully")

        except Exception as e:
            logger.error(f"Failed to create indexes: {str(e)}")
            raise

    async def health_check(self) -> bool:
        """Check database health"""
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                return result == 1
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return False

    @asynccontextmanager
    async def get_connection(self):
        """Get database connection from pool"""
        async with self.pool.acquire() as conn:
            yield conn

    @asynccontextmanager
    async def get_transaction(self):
        """Get database transaction"""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                yield conn

    async def close(self):
        """Close database connections"""
        if self.pool:
            await self.pool.close()
        if self.engine:
            self.engine.dispose()

    # Alert operations
    async def create_alert(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new alert"""
        async with self.get_transaction() as conn:
            query = """
                INSERT INTO alerts (alert_type, message, priority, status, metadata,
                                  stock_code, user_id, expires_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING *
            """
            row = await conn.fetchrow(
                query,
                alert_data['alert_type'],
                alert_data['message'],
                alert_data['priority'],
                alert_data.get('status', 'active'),
                json.dumps(alert_data.get('metadata', {})),
                alert_data.get('stock_code'),
                alert_data.get('user_id'),
                alert_data.get('expires_at')
            )
            return dict(row)

    async def get_alerts(self, user_id: str = None, limit: int = 100, offset: int = 0,
                        status: str = None, priority: str = None,
                        start_date: datetime = None, end_date: datetime = None) -> List[Dict[str, Any]]:
        """Get alerts with filtering"""
        conditions = []
        params = []
        param_count = 0

        base_query = "SELECT * FROM alerts WHERE 1=1"

        if user_id:
            param_count += 1
            conditions.append(f" AND user_id = ${param_count}")
            params.append(user_id)

        if status:
            param_count += 1
            conditions.append(f" AND status = ${param_count}")
            params.append(status)

        if priority:
            param_count += 1
            conditions.append(f" AND priority = ${param_count}")
            params.append(priority)

        if start_date:
            param_count += 1
            conditions.append(f" AND created_at >= ${param_count}")
            params.append(start_date)

        if end_date:
            param_count += 1
            conditions.append(f" AND created_at <= ${param_count}")
            params.append(end_date)

        query = base_query + "".join(conditions) + f" ORDER BY created_at DESC LIMIT ${param_count + 1} OFFSET ${param_count + 2}"
        params.extend([limit, offset])

        async with self.get_connection() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]

    async def update_alert_status(self, alert_id: int, status: str, notes: str = None,
                                user_id: str = None) -> Dict[str, Any]:
        """Update alert status"""
        async with self.get_transaction() as conn:
            update_fields = ["status = $2", "updated_at = NOW()"]
            params = [alert_id, status]
            param_count = 2

            if status == "acknowledged" and user_id:
                param_count += 1
                update_fields.extend([f"acknowledged_at = NOW()", f"acknowledged_by = ${param_count}"])
                params.append(user_id)

            query = f"""
                UPDATE alerts
                SET {', '.join(update_fields)}
                WHERE id = $1
                RETURNING *
            """

            row = await conn.fetchrow(query, *params)
            return dict(row) if row else None

    # Trading signal operations
    async def save_trading_signals(self, signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Bulk save trading signals"""
        async with self.get_transaction() as conn:
            query = """
                INSERT INTO trading_signals (
                    date, stock_code, sector, signal_type, composite_score,
                    confidence, position_size, current_price, volume,
                    technical_score, fundamental_score, sentiment_score,
                    risk_adjusted, metadata
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                RETURNING *
            """

            results = []
            for signal in signals:
                row = await conn.fetchrow(
                    query,
                    signal['date'],
                    signal['stock_code'],
                    signal.get('sector'),
                    signal['signal_type'],
                    signal['composite_score'],
                    signal['confidence'],
                    signal['position_size'],
                    signal['current_price'],
                    signal.get('volume'),
                    signal.get('technical_score'),
                    signal.get('fundamental_score'),
                    signal.get('sentiment_score'),
                    signal.get('risk_adjusted', False),
                    json.dumps(signal.get('metadata', {}))
                )
                results.append(dict(row))

            return results

    async def get_daily_signals(self, date: datetime) -> List[Dict[str, Any]]:
        """Get trading signals for specific date"""
        async with self.get_connection() as conn:
            query = """
                SELECT * FROM trading_signals
                WHERE DATE(date) = DATE($1)
                ORDER BY confidence DESC, composite_score DESC
            """
            rows = await conn.fetch(query, date)
            return [dict(row) for row in rows]

    # Portfolio operations
    async def update_position(self, stock_code: str, quantity: int, average_price: float,
                            user_id: str) -> Dict[str, Any]:
        """Update portfolio position"""
        async with self.get_transaction() as conn:
            # Check if position exists
            existing = await conn.fetchrow(
                "SELECT * FROM portfolio WHERE stock_code = $1 AND user_id = $2",
                stock_code, user_id
            )

            if existing:
                # Update existing position
                query = """
                    UPDATE portfolio
                    SET quantity = $3, average_price = $4, last_updated = NOW()
                    WHERE stock_code = $1 AND user_id = $2
                    RETURNING *
                """
                row = await conn.fetchrow(query, stock_code, user_id, quantity, average_price)
            else:
                # Create new position
                query = """
                    INSERT INTO portfolio (stock_code, quantity, average_price, user_id)
                    VALUES ($1, $2, $3, $4)
                    RETURNING *
                """
                row = await conn.fetchrow(query, stock_code, quantity, average_price, user_id)

            return dict(row)

    async def get_portfolio_positions(self, user_id: str = None) -> List[Dict[str, Any]]:
        """Get current portfolio positions"""
        async with self.get_connection() as conn:
            if user_id:
                query = "SELECT * FROM portfolio WHERE user_id = $1 AND quantity > 0"
                rows = await conn.fetch(query, user_id)
            else:
                query = "SELECT * FROM portfolio WHERE quantity > 0"
                rows = await conn.fetch(query)

            return [dict(row) for row in rows]

    # Market data operations
    async def save_market_data(self, market_data: List[Dict[str, Any]]) -> int:
        """Save market data points"""
        async with self.get_transaction() as conn:
            query = """
                INSERT INTO market_data (
                    stock_code, timestamp, open_price, high_price, low_price,
                    close_price, volume, trade_count, vwap, bid_price, ask_price,
                    bid_size, ask_size
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            """

            count = 0
            for data_point in market_data:
                await conn.execute(
                    query,
                    data_point['stock_code'],
                    data_point['timestamp'],
                    data_point.get('open_price'),
                    data_point.get('high_price'),
                    data_point.get('low_price'),
                    data_point.get('close_price'),
                    data_point.get('volume'),
                    data_point.get('trade_count'),
                    data_point.get('vwap'),
                    data_point.get('bid_price'),
                    data_point.get('ask_price'),
                    data_point.get('bid_size'),
                    data_point.get('ask_size')
                )
                count += 1

            return count

    async def get_latest_prices(self, stock_codes: List[str]) -> Dict[str, float]:
        """Get latest prices for stocks"""
        async with self.get_connection() as conn:
            query = """
                SELECT DISTINCT ON (stock_code) stock_code, close_price
                FROM market_data
                WHERE stock_code = ANY($1)
                ORDER BY stock_code, timestamp DESC
            """
            rows = await conn.fetch(query, stock_codes)
            return {row['stock_code']: row['close_price'] for row in rows}

    # System metrics
    async def save_system_metric(self, metric_name: str, metric_value: float,
                               metadata: Dict[str, Any] = None):
        """Save system performance metric"""
        async with self.get_connection() as conn:
            query = """
                INSERT INTO system_metrics (metric_name, metric_value, metadata)
                VALUES ($1, $2, $3)
            """
            await conn.execute(
                query,
                metric_name,
                metric_value,
                json.dumps(metadata or {})
            )


# Database dependency for FastAPI
async def get_db():
    """FastAPI dependency for database access"""
    db_manager = DatabaseManager()
    try:
        yield db_manager
    finally:
        await db_manager.close()