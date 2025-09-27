"""
Minimal FastAPI Application for Indonesian Quantitative Trading System
Simplified version to get the system running quickly
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Indonesian Quantitative Trading System",
    description="Minimal version for quick startup",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock data for testing
MOCK_USER = {
    "id": "1",
    "username": "admin",
    "email": "admin@example.com",
    "role": "admin"
}

MOCK_TOKEN = "mock_token_123"

# Health Check
@app.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "trading-system",
        "version": "1.0.0"
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Indonesian Quantitative Trading System API", "status": "running"}

# Authentication endpoints
@app.post("/auth/login")
async def login(credentials: Dict[str, str]):
    """Simple login endpoint"""
    logger.info(f"Login attempt received: {credentials}")
    username = credentials.get("username", "")
    password = credentials.get("password", "")
    logger.info(f"Username: '{username}', Password: '{password}'")

    # Simple mock authentication
    if (username == "admin" and password == "admin123") or (username == "trader" and password == "trader123"):
        return {
            "access_token": MOCK_TOKEN,
            "refresh_token": f"refresh_{MOCK_TOKEN}",
            "token_type": "bearer",
            "expires_in": 3600,
            "user": MOCK_USER
        }
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/auth/me")
async def get_current_user():
    """Get current user info"""
    return MOCK_USER

# Trading endpoints
@app.get("/signals/daily")
async def get_daily_signals():
    """Get daily trading signals"""
    return {
        "date": datetime.now().date().isoformat(),
        "signals": [
            {
                "id": 1,
                "date": datetime.now().date().isoformat(),
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
                "metadata": {"target_price": 9200, "stop_loss": 8400},
                "generated_at": datetime.now().isoformat()
            },
            {
                "id": 2,
                "date": datetime.now().date().isoformat(),
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
                "metadata": {"target_price": 4800, "stop_loss": 4350},
                "generated_at": datetime.now().isoformat()
            },
            {
                "id": 3,
                "date": datetime.now().date().isoformat(),
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
                "metadata": {"target_price": 3350, "stop_loss": 3720},
                "generated_at": datetime.now().isoformat()
            }
        ],
        "total_signals": 3,
        "generated_at": datetime.now().isoformat()
    }

@app.get("/portfolio/summary")
async def get_portfolio_summary():
    """Get portfolio summary"""
    return {
        "total_positions": 12,
        "total_market_value": 1000000000,  # 1B IDR
        "total_cost_basis": 984500000,     # 984.5M IDR (cost basis)
        "total_unrealized_pnl": 15500000,  # 15.5M IDR
        "total_unrealized_pnl_percent": 1.57,
        "sector_breakdown": {
            "Banking": 35.5,
            "Consumer Goods": 22.3,
            "Technology": 18.7,
            "Mining": 12.8,
            "Telecommunications": 10.7
        },
        "cash_available": 250000000,       # 250M IDR
        "portfolio_beta": 1.12,
        "sharpe_ratio": 1.45,
        "max_drawdown": 8.2,
        "last_updated": datetime.now().isoformat()
    }

@app.get("/portfolio/positions")
async def get_positions():
    """Get current positions"""
    return [
        {
            "stock_code": "BBCA.JK",
            "quantity": 10000,
            "average_price": 8500,
            "current_price": 8750,
            "market_value": 87500000,
            "unrealized_pnl": 2500000,
            "unrealized_pnl_percent": 2.94
        },
        {
            "stock_code": "BBRI.JK",
            "quantity": 15000,
            "average_price": 4400,
            "current_price": 4580,
            "market_value": 68700000,
            "unrealized_pnl": 2700000,
            "unrealized_pnl_percent": 4.09
        }
    ]

@app.get("/alerts")
async def get_alerts():
    """Get recent alerts"""
    return [
        {
            "id": 1,
            "type": "PRICE_TARGET",
            "message": "BBCA reached target price of 8750",
            "priority": "high",
            "status": "active",
            "created_at": datetime.now().isoformat(),
            "stock_code": "BBCA.JK"
        },
        {
            "id": 2,
            "type": "RISK_WARNING",
            "message": "Portfolio concentration risk detected",
            "priority": "medium",
            "status": "active",
            "created_at": datetime.now().isoformat()
        }
    ]

@app.get("/market/status")
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
        "next_open": "2024-01-01T09:00:00",
        "next_close": "2024-01-01T15:49:00"
    }

@app.get("/risk/overview")
async def get_risk_overview():
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
            "critical": 0,
            "high": 1,
            "medium": 2,
            "low": 3
        },
        "monitoring_status": "active",
        "last_check": datetime.now().isoformat(),
        "portfolio_risk_score": 3.2
    }

@app.get("/backtesting/performance")
async def get_backtesting_performance():
    """Get backtesting performance data"""
    return {
        "total_trades": 245,
        "win_rate": 68.2,
        "total_profit": 185420000,  # 185.42M IDR
        "total_profit_formatted": "Rp 185.42M",
        "avg_return": 2.85,
        "avg_holding_days": 12.5,
        "best_trade": 24580000,  # 24.58M IDR
        "worst_trade": -8920000,  # -8.92M IDR
        "sharpe_ratio": 1.52,
        "max_drawdown": 12.8,
        "sortino_ratio": 2.14,
        "calmar_ratio": 1.85,
        "total_return": 23.7,
        "annual_return": 19.4,
        "monthly_returns": [
            {"month": "Jan", "return": 3.2},
            {"month": "Feb", "return": -1.8},
            {"month": "Mar", "return": 4.1},
            {"month": "Apr", "return": 2.7},
            {"month": "May", "return": -0.9},
            {"month": "Jun", "return": 3.8},
            {"month": "Jul", "return": 1.6},
            {"month": "Aug", "return": 2.3},
            {"month": "Sep", "return": 4.9},
            {"month": "Oct", "return": 1.2},
            {"month": "Nov", "return": 2.8},
            {"month": "Dec", "return": 3.1}
        ],
        "sector_performance": {
            "Banking": {"return": 21.5, "trades": 78},
            "Consumer Goods": {"return": 18.2, "trades": 45},
            "Technology": {"return": 28.7, "trades": 32},
            "Mining": {"return": 15.8, "trades": 42},
            "Telecommunications": {"return": 12.3, "trades": 48}
        },
        "confidence_analysis": {
            "high_confidence": {"trades": 82, "success_rate": 78.2, "avg_return": 4.1},
            "medium_confidence": {"trades": 115, "success_rate": 65.8, "avg_return": 2.8},
            "low_confidence": {"trades": 48, "success_rate": 58.3, "avg_return": 1.2}
        },
        "period_start": "2023-01-01",
        "period_end": "2024-09-27",
        "generated_at": datetime.now().isoformat()
    }

@app.get("/analytics/performance")
async def get_performance():
    """Get performance analytics"""
    return {
        "total_return": 18.5,
        "annual_return": 22.3,
        "sharpe_ratio": 1.45,
        "max_drawdown": 8.2,
        "win_rate": 67.5,
        "profit_factor": 2.1,
        "daily_returns": [1.2, -0.8, 2.1, 0.5, 1.8, -1.1, 2.3]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)