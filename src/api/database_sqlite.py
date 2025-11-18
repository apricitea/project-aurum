"""
SQLite Database Manager for Local Development
Simplified version for local testing without external dependencies
"""

import logging
from typing import Optional
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager

from .database import Base, User, Alert, TradingSignal, Portfolio, RiskAlert, MarketData, SystemMetric, SignalGenerationTask
from .config import settings

logger = logging.getLogger(__name__)


class SQLiteDatabaseManager:
    """
    SQLite database manager for local development
    Simpler alternative to PostgreSQL for development and testing
    """

    def __init__(self, db_path: str = "data/trading_system.db"):
        self.db_path = db_path
        self.engine = None
        self.session_factory = None
        self._connection_string = f"sqlite:///{db_path}"

    async def initialize(self):
        """Initialize SQLite database and create tables"""
        try:
            # Create SQLAlchemy engine for SQLite
            self.engine = create_engine(
                self._connection_string,
                connect_args={"check_same_thread": False},  # Required for SQLite with multiple threads
                echo=settings.DEBUG
            )

            self.session_factory = sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False
            )

            # Create all tables
            await self.create_tables()

            # Create indexes for performance
            await self.create_indexes()

            logger.info(f"SQLite database initialized successfully at {self.db_path}")

        except Exception as e:
            logger.error(f"Failed to initialize SQLite database: {str(e)}")
            raise

    async def create_tables(self):
        """Create database tables if they don't exist"""
        try:
            Base.metadata.create_all(self.engine)
            logger.info("Database tables created successfully")

        except Exception as e:
            logger.error(f"Failed to create tables: {str(e)}")
            raise

    async def create_indexes(self):
        """Create performance indexes using SQLite-compatible syntax"""
        try:
            with self.engine.connect() as conn:
                # Alert indexes
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_alerts_status_created
                    ON alerts(status, created_at DESC)
                """)

                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_alerts_user_type
                    ON alerts(user_id, alert_type)
                """)

                # Trading signal indexes
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_signals_date_stock
                    ON trading_signals(date DESC, stock_code)
                """)

                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_signals_type_confidence
                    ON trading_signals(signal_type, confidence DESC)
                """)

                # Portfolio indexes
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_portfolio_user_stock
                    ON portfolio(user_id, stock_code)
                """)

                # Market data indexes
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_market_data_stock_time
                    ON market_data(stock_code, timestamp DESC)
                """)

                # Risk alert indexes
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_risk_alerts_active_type
                    ON risk_alerts(is_active, alert_type, created_at DESC)
                """)

                conn.commit()

            logger.info("Database indexes created successfully")

        except Exception as e:
            logger.error(f"Failed to create indexes: {str(e)}")
            # Don't fail if indexes already exist
            pass

    @contextmanager
    def get_session(self) -> Session:
        """Get a database session"""
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {str(e)}")
            raise
        finally:
            session.close()

    async def close(self):
        """Close database connections"""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connections closed")


# Global instance
db_manager: Optional[SQLiteDatabaseManager] = None


def get_db() -> Session:
    """Dependency to get database session"""
    if not db_manager:
        raise RuntimeError("Database not initialized")

    with db_manager.get_session() as session:
        yield session
