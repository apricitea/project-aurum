#!/usr/bin/env python3
"""
Database Initialization Script
Creates database tables and initial data for local development
"""

import sys
import os
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from api.database_sqlite import SQLiteDatabaseManager
from api.database import User, Alert, TradingSignal, Portfolio
from datetime import datetime, timedelta
import uuid
import bcrypt
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def init_database():
    """Initialize database with tables and seed data"""
    logger.info("🚀 Initializing database...")

    # Create database manager
    db_manager = SQLiteDatabaseManager(db_path="data/trading_system.db")
    await db_manager.initialize()

    logger.info("✅ Database tables created successfully")

    # Create initial admin user
    await create_users(db_manager)

    # Create sample data
    await create_sample_signals(db_manager)
    await create_sample_portfolio(db_manager)
    await create_sample_alerts(db_manager)

    await db_manager.close()

    logger.info("🎉 Database initialization complete!")
    logger.info("📍 Database location: data/trading_system.db")
    logger.info("\n📝 Demo Credentials:")
    logger.info("   Admin:  admin / admin123")
    logger.info("   Trader: trader / trader123")


async def create_users(db_manager: SQLiteDatabaseManager):
    """Create initial users"""
    logger.info("Creating users...")

    with db_manager.get_session() as session:
        # Check if users already exist
        existing_admin = session.query(User).filter_by(username="admin").first()
        if existing_admin:
            logger.info("Users already exist, skipping...")
            return

        # Create admin user
        admin_password_hash = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()
        admin = User(
            id=uuid.uuid4(),
            username="admin",
            email="admin@aurum.local",
            password_hash=admin_password_hash,
            role="admin",
            permissions={
                "view_dashboard": True,
                "manage_signals": True,
                "manage_portfolio": True,
                "manage_alerts": True,
                "manage_users": True
            },
            is_active=True,
            created_at=datetime.utcnow()
        )

        # Create trader user
        trader_password_hash = bcrypt.hashpw("trader123".encode(), bcrypt.gensalt()).decode()
        trader = User(
            id=uuid.uuid4(),
            username="trader",
            email="trader@aurum.local",
            password_hash=trader_password_hash,
            role="trader",
            permissions={
                "view_dashboard": True,
                "manage_portfolio": True
            },
            is_active=True,
            created_at=datetime.utcnow()
        )

        session.add(admin)
        session.add(trader)
        session.commit()

        logger.info("✅ Created users: admin, trader")


async def create_sample_signals(db_manager: SQLiteDatabaseManager):
    """Create sample trading signals"""
    logger.info("Creating sample trading signals...")

    signals_data = [
        {
            "stock_code": "BBCA.JK",
            "sector": "Banking",
            "signal_type": "BUY",
            "composite_score": 8.5,
            "confidence": 0.85,
            "position_size": 5.2,
            "current_price": 8750,
            "volume": 15420000,
            "technical_score": 8.8,
            "fundamental_score": 8.2,
            "sentiment_score": 8.5,
            "risk_adjusted": True,
            "meta_data": {"target_price": 9200, "stop_loss": 8400, "reason": "Strong fundamentals and technical breakout"}
        },
        {
            "stock_code": "BBRI.JK",
            "sector": "Banking",
            "signal_type": "HOLD",
            "composite_score": 7.2,
            "confidence": 0.72,
            "position_size": 3.8,
            "current_price": 4580,
            "volume": 12880000,
            "technical_score": 7.5,
            "fundamental_score": 6.9,
            "sentiment_score": 7.2,
            "risk_adjusted": True,
            "meta_data": {"target_price": 4800, "stop_loss": 4350, "reason": "Consolidation pattern"}
        },
        {
            "stock_code": "TLKM.JK",
            "sector": "Telecommunications",
            "signal_type": "SELL",
            "composite_score": 4.2,
            "confidence": 0.68,
            "position_size": 2.1,
            "current_price": 3580,
            "volume": 8950000,
            "technical_score": 4.0,
            "fundamental_score": 4.5,
            "sentiment_score": 4.1,
            "risk_adjusted": True,
            "meta_data": {"target_price": 3350, "stop_loss": 3720, "reason": "Weakening fundamentals"}
        },
        {
            "stock_code": "ASII.JK",
            "sector": "Consumer Goods",
            "signal_type": "STRONG_BUY",
            "composite_score": 9.1,
            "confidence": 0.91,
            "position_size": 6.5,
            "current_price": 5200,
            "volume": 18500000,
            "technical_score": 9.2,
            "fundamental_score": 8.9,
            "sentiment_score": 9.2,
            "risk_adjusted": True,
            "meta_data": {"target_price": 5800, "stop_loss": 4950, "reason": "Exceptional growth prospects"}
        },
        {
            "stock_code": "UNVR.JK",
            "sector": "Consumer Goods",
            "signal_type": "BUY",
            "composite_score": 7.8,
            "confidence": 0.78,
            "position_size": 4.5,
            "current_price": 4150,
            "volume": 6800000,
            "technical_score": 8.1,
            "fundamental_score": 7.5,
            "sentiment_score": 7.8,
            "risk_adjusted": True,
            "meta_data": {"target_price": 4500, "stop_loss": 3950, "reason": "Defensive stock with stable dividends"}
        }
    ]

    with db_manager.get_session() as session:
        today = datetime.now()

        for signal_data in signals_data:
            signal = TradingSignal(
                date=today,
                generated_at=today,
                **signal_data
            )
            session.add(signal)

        session.commit()

    logger.info(f"✅ Created {len(signals_data)} sample trading signals")


async def create_sample_portfolio(db_manager: SQLiteDatabaseManager):
    """Create sample portfolio positions"""
    logger.info("Creating sample portfolio...")

    # Get admin user
    with db_manager.get_session() as session:
        admin_user = session.query(User).filter_by(username="admin").first()

        positions_data = [
            {
                "stock_code": "BBCA.JK",
                "quantity": 10000,
                "average_price": 8500,
                "current_price": 8750,
                "sector": "Banking",
                "market_value": 87500000,
                "unrealized_pnl": 2500000,
                "position_size_percent": 8.75,
                "user_id": admin_user.id
            },
            {
                "stock_code": "BBRI.JK",
                "quantity": 15000,
                "average_price": 4400,
                "current_price": 4580,
                "sector": "Banking",
                "market_value": 68700000,
                "unrealized_pnl": 2700000,
                "position_size_percent": 6.87,
                "user_id": admin_user.id
            },
            {
                "stock_code": "ASII.JK",
                "quantity": 8000,
                "average_price": 5100,
                "current_price": 5200,
                "sector": "Consumer Goods",
                "market_value": 41600000,
                "unrealized_pnl": 800000,
                "position_size_percent": 4.16,
                "user_id": admin_user.id
            }
        ]

        for position_data in positions_data:
            position = Portfolio(**position_data)
            session.add(position)

        session.commit()

    logger.info(f"✅ Created {len(positions_data)} sample portfolio positions")


async def create_sample_alerts(db_manager: SQLiteDatabaseManager):
    """Create sample alerts"""
    logger.info("Creating sample alerts...")

    with db_manager.get_session() as session:
        admin_user = session.query(User).filter_by(username="admin").first()

        alerts_data = [
            {
                "alert_type": "PRICE_TARGET",
                "message": "BBCA reached target price of 8750",
                "priority": "high",
                "status": "active",
                "stock_code": "BBCA.JK",
                "user_id": admin_user.id,
                "meta_data": {"target_price": 8750, "current_price": 8750}
            },
            {
                "alert_type": "RISK_WARNING",
                "message": "Portfolio concentration risk detected in Banking sector",
                "priority": "medium",
                "status": "active",
                "user_id": admin_user.id,
                "meta_data": {"sector": "Banking", "concentration": 15.62}
            },
            {
                "alert_type": "SIGNAL_GENERATED",
                "message": "New STRONG_BUY signal generated for ASII.JK",
                "priority": "high",
                "status": "active",
                "stock_code": "ASII.JK",
                "user_id": admin_user.id,
                "meta_data": {"signal_type": "STRONG_BUY", "confidence": 0.91}
            }
        ]

        for alert_data in alerts_data:
            alert = Alert(**alert_data)
            session.add(alert)

        session.commit()

    logger.info(f"✅ Created {len(alerts_data)} sample alerts")


if __name__ == "__main__":
    asyncio.run(init_database())
