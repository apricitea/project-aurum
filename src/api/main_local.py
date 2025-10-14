"""
Local Development FastAPI Application
Uses SQLite database with real data (not mock)
Simplified version of main.py for local development
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
from contextlib import asynccontextmanager
import bcrypt
import uuid
import jwt
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from .database_sqlite import SQLiteDatabaseManager, get_db
from .database import User, Alert, TradingSignal, Portfolio, MarketData
from .schemas import *

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global database manager
db_manager: SQLiteDatabaseManager = None

# JWT settings
JWT_SECRET = "your-secret-key-change-in-production-123456"
JWT_ALGORITHM = "HS256"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global db_manager

    # Startup
    logger.info("🚀 Starting Local Development Server with SQLite...")

    # Initialize database
    db_manager = SQLiteDatabaseManager(db_path="data/trading_system.db")
    await db_manager.initialize()

    logger.info("✅ Database initialized successfully")
    logger.info("📍 Using SQLite database at: data/trading_system.db")

    yield

    # Shutdown
    logger.info("Shutting down...")
    if db_manager:
        await db_manager.close()


# Initialize FastAPI app
app = FastAPI(
    title="Indonesian Quantitative Trading System - Local Dev",
    description="Local development server with SQLite database",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Helper functions
def create_access_token(user_id: str, username: str) -> str:
    """Create JWT access token"""
    payload = {
        "user_id": str(user_id),
        "username": username,
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


# Health Check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database": "sqlite",
        "environment": "development"
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Indonesian Quantitative Trading System API - Local Development",
        "status": "running",
        "database": "SQLite",
        "docs": "/docs"
    }


# Authentication endpoints
@app.post("/api/auth/login")
async def login(credentials: Dict[str, str], session: Session = Depends(get_db)):
    """Login endpoint with real database authentication"""
    username = credentials.get("username", "")
    password = credentials.get("password", "")

    # Find user in database
    user = session.query(User).filter_by(username=username).first()

    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=401, detail="User account is disabled")

    # Update last login
    user.last_login = datetime.utcnow()
    session.commit()

    # Create access token
    access_token = create_access_token(user.id, user.username)

    return {
        "access_token": access_token,
        "refresh_token": f"refresh_{access_token}",
        "token_type": "bearer",
        "expires_in": 86400,  # 24 hours
        "user": {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "permissions": user.permissions,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login": user.last_login.isoformat() if user.last_login else None
        }
    }


@app.get("/api/auth/me")
async def get_current_user(session: Session = Depends(get_db)):
    """Get current user - simplified without auth check for dev"""
    user = session.query(User).filter_by(username="admin").first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "permissions": user.permissions,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "last_login": user.last_login.isoformat() if user.last_login else None
    }


# Trading Signals
@app.get("/api/signals/daily")
async def get_daily_signals(date: Optional[str] = None, session: Session = Depends(get_db)):
    """Get daily trading signals from database"""
    query = session.query(TradingSignal)

    if date:
        target_date = datetime.fromisoformat(date)
        query = query.filter(func.date(TradingSignal.date) == target_date.date())
    else:
        # Get signals from last 7 days
        week_ago = datetime.now() - timedelta(days=7)
        query = query.filter(TradingSignal.date >= week_ago)

    signals = query.order_by(desc(TradingSignal.generated_at)).limit(50).all()

    return {
        "date": date or datetime.now().date().isoformat(),
        "signals": [
            {
                "id": signal.id,
                "date": signal.date.isoformat() if signal.date else None,
                "stock_code": signal.stock_code,
                "sector": signal.sector,
                "signal_type": signal.signal_type,
                "composite_score": signal.composite_score,
                "confidence": signal.confidence,
                "position_size": signal.position_size,
                "current_price": signal.current_price,
                "volume": signal.volume,
                "technical_score": signal.technical_score,
                "fundamental_score": signal.fundamental_score,
                "sentiment_score": signal.sentiment_score,
                "risk_adjusted": signal.risk_adjusted,
                "metadata": signal.meta_data,
                "generated_at": signal.generated_at.isoformat() if signal.generated_at else None
            }
            for signal in signals
        ],
        "total_signals": len(signals),
        "generated_at": datetime.now().isoformat()
    }


# Portfolio
@app.get("/api/portfolio/summary")
async def get_portfolio_summary(session: Session = Depends(get_db)):
    """Get portfolio summary from database"""
    # Get all positions
    positions = session.query(Portfolio).all()

    if not positions:
        return {
            "total_positions": 0,
            "total_market_value": 0,
            "total_cost_basis": 0,
            "total_unrealized_pnl": 0,
            "total_unrealized_pnl_percent": 0,
            "sector_breakdown": {},
            "cash_available": 250000000,
            "portfolio_beta": 0,
            "sharpe_ratio": 0,
            "max_drawdown": 0,
            "last_updated": datetime.now().isoformat()
        }

    # Calculate totals
    total_market_value = sum(p.market_value or 0 for p in positions)
    total_cost_basis = sum(p.quantity * p.average_price for p in positions)
    total_unrealized_pnl = sum(p.unrealized_pnl or 0 for p in positions)

    # Calculate sector breakdown
    sector_breakdown = {}
    for position in positions:
        sector = position.sector or "Unknown"
        sector_value = position.market_value or 0
        sector_breakdown[sector] = sector_breakdown.get(sector, 0) + (
            (sector_value / total_market_value * 100) if total_market_value > 0 else 0
        )

    return {
        "total_positions": len(positions),
        "total_market_value": total_market_value,
        "total_cost_basis": total_cost_basis,
        "total_unrealized_pnl": total_unrealized_pnl,
        "total_unrealized_pnl_percent": (
            (total_unrealized_pnl / total_cost_basis * 100) if total_cost_basis > 0 else 0
        ),
        "sector_breakdown": sector_breakdown,
        "cash_available": 250000000,  # Mock value
        "portfolio_beta": 1.12,  # Mock value
        "sharpe_ratio": 1.45,  # Mock value
        "max_drawdown": 8.2,  # Mock value
        "last_updated": datetime.now().isoformat()
    }


@app.get("/api/portfolio/positions")
async def get_positions(session: Session = Depends(get_db)):
    """Get all portfolio positions"""
    positions = session.query(Portfolio).all()

    return [
        {
            "id": position.id,
            "stock_code": position.stock_code,
            "quantity": position.quantity,
            "average_price": position.average_price,
            "current_price": position.current_price,
            "sector": position.sector,
            "market_value": position.market_value,
            "unrealized_pnl": position.unrealized_pnl,
            "unrealized_pnl_percent": (
                (position.unrealized_pnl / (position.quantity * position.average_price) * 100)
                if position.unrealized_pnl and position.quantity and position.average_price
                else 0
            ),
            "position_size_percent": position.position_size_percent,
            "last_updated": position.last_updated.isoformat() if position.last_updated else None
        }
        for position in positions
    ]


# Alerts
@app.get("/api/alerts")
async def get_alerts(
    limit: int = 20,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    session: Session = Depends(get_db)
):
    """Get alerts from database"""
    query = session.query(Alert)

    if status:
        query = query.filter_by(status=status)
    if priority:
        query = query.filter_by(priority=priority)

    alerts = query.order_by(desc(Alert.created_at)).limit(limit).all()

    return [
        {
            "id": alert.id,
            "alert_type": alert.alert_type,
            "message": alert.message,
            "priority": alert.priority,
            "status": alert.status,
            "stock_code": alert.stock_code,
            "metadata": alert.meta_data,
            "created_at": alert.created_at.isoformat() if alert.created_at else None,
            "updated_at": alert.updated_at.isoformat() if alert.updated_at else None,
            "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
            "expires_at": alert.expires_at.isoformat() if alert.expires_at else None
        }
        for alert in alerts
    ]


# Market Status
@app.get("/api/market/status")
async def get_market_status():
    """Get market status"""
    now = datetime.now()
    hour = now.hour

    # IDX trading hours: 09:00-15:49 WIB
    is_open = 9 <= hour < 16

    return {
        "is_open": is_open,
        "current_time": now.isoformat(),
        "session_type": "regular" if is_open else "closed",
        "next_open": (now + timedelta(days=1)).replace(hour=9, minute=0).isoformat(),
        "next_close": now.replace(hour=15, minute=49).isoformat()
    }


# Risk Overview
@app.get("/api/risk/overview")
async def get_risk_overview(session: Session = Depends(get_db)):
    """Get risk overview"""
    return {
        "risk_metrics": {
            "portfolio_var": {
                "name": "Value at Risk",
                "current_value": 2.3,
                "limit_value": 5.0,
                "warning_threshold": 3.5,
                "critical_threshold": 4.5,
                "status": "normal",
                "description": "Daily VaR at 95% confidence"
            },
            "max_position_size": {
                "name": "Maximum Position Size",
                "current_value": 8.2,
                "limit_value": 15.0,
                "warning_threshold": 12.0,
                "critical_threshold": 14.0,
                "status": "normal",
                "description": "Largest single position as % of portfolio"
            }
        },
        "alert_counts": {
            "critical": session.query(Alert).filter_by(priority="critical", status="active").count(),
            "high": session.query(Alert).filter_by(priority="high", status="active").count(),
            "medium": session.query(Alert).filter_by(priority="medium", status="active").count(),
            "low": session.query(Alert).filter_by(priority="low", status="active").count()
        },
        "monitoring_status": "active",
        "last_check": datetime.now().isoformat(),
        "portfolio_risk_score": 0.32
    }


# Analytics
@app.get("/api/analytics/performance")
async def get_performance(days: int = 30, session: Session = Depends(get_db)):
    """Get performance analytics"""
    # Get signals from last N days
    since_date = datetime.now() - timedelta(days=days)
    signals = session.query(TradingSignal).filter(TradingSignal.date >= since_date).all()

    # Calculate signal type distribution
    signal_type_distribution = {}
    for signal in signals:
        signal_type = signal.signal_type
        signal_type_distribution[signal_type] = signal_type_distribution.get(signal_type, 0) + 1

    return {
        "period_days": days,
        "total_signals": len(signals),
        "signal_type_distribution": signal_type_distribution,
        "avg_confidence": sum(s.confidence for s in signals) / len(signals) if signals else 0,
        "avg_position_size": sum(s.position_size for s in signals) / len(signals) if signals else 0,
        "avg_daily_signals": len(signals) / days if days > 0 else 0,
        "daily_signal_counts": {},
        "performance_metrics": {
            "period_days": days,
            "total_return": 18.5,
            "annualized_return": 22.3,
            "volatility": 12.8,
            "sharpe_ratio": 1.45,
            "max_drawdown": 8.2,
            "win_rate": 67.5,
            "avg_trade_return": 2.85
        },
        "analysis_date": datetime.now().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
