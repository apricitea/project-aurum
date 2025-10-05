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
@app.post("/api/auth/login")
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

@app.get("/api/auth/me")
async def get_current_user():
    """Get current user info"""
    return MOCK_USER

# Trading endpoints
@app.get("/api/signals/daily")
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

@app.get("/api/portfolio/summary")
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

@app.get("/api/portfolio/positions")
async def get_positions():
    """Get current positions"""
    return [
        {
            "id": 1,
            "stock_code": "BBCA.JK",
            "quantity": 10000,
            "average_price": 8500,
            "current_price": 8750,
            "sector": "Banking",
            "market_value": 87500000,
            "unrealized_pnl": 2500000,
            "unrealized_pnl_percent": 2.94,
            "position_size_percent": 8.75,
            "last_updated": datetime.now().isoformat()
        },
        {
            "id": 2,
            "stock_code": "BBRI.JK",
            "quantity": 15000,
            "average_price": 4400,
            "current_price": 4580,
            "sector": "Banking",
            "market_value": 68700000,
            "unrealized_pnl": 2700000,
            "unrealized_pnl_percent": 4.09,
            "position_size_percent": 6.87,
            "last_updated": datetime.now().isoformat()
        }
    ]

@app.get("/api/alerts")
async def get_alerts():
    """Get recent alerts"""
    return [
        {
            "id": 1,
            "alert_type": "PRICE_TARGET",
            "message": "BBCA reached target price of 8750",
            "priority": "high",
            "status": "active",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "stock_code": "BBCA.JK"
        },
        {
            "id": 2,
            "alert_type": "RISK_WARNING",
            "message": "Portfolio concentration risk detected",
            "priority": "medium",
            "status": "active",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
    ]

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
        "next_open": "2024-01-01T09:00:00",
        "next_close": "2024-01-01T15:49:00"
    }

@app.get("/api/risk/overview")
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

@app.get("/api/backtest/results/{backtest_id}")
async def get_backtest_results(backtest_id: str):
    """Get backtest results by ID"""
    return await get_backtesting_performance()

@app.get("/api/analytics/performance")
async def get_analytics_performance(days: int = 30):
    """Get performance analytics"""
    return {
        "period_days": days,
        "total_signals": 245,
        "signal_type_distribution": {
            "BUY": 98,
            "SELL": 87,
            "HOLD": 60
        },
        "avg_confidence": 0.725,
        "avg_position_size": 4.2,
        "avg_daily_signals": 8.2,
        "daily_signal_counts": {
            "2024-01-01": 8,
            "2024-01-02": 7,
            "2024-01-03": 9
        },
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

@app.get("/backtesting/performance")
async def get_backtesting_performance():
    """Get backtesting performance data"""
    return {
        "performance": {
            "overview": {
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
                "annual_return": 19.4
            },
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
            "sector_analysis": {
                "Banking": {"total_trades": 78, "win_rate": 71.8, "avg_return": 2.9, "total_profit": 45280000},
                "Consumer Goods": {"total_trades": 45, "win_rate": 66.7, "avg_return": 2.3, "total_profit": 28150000},
                "Technology": {"total_trades": 32, "win_rate": 75.0, "avg_return": 3.8, "total_profit": 38920000},
                "Mining": {"total_trades": 42, "win_rate": 61.9, "avg_return": 1.9, "total_profit": 22480000},
                "Telecommunications": {"total_trades": 48, "win_rate": 58.3, "avg_return": 1.4, "total_profit": 15590000}
            },
            "confidence_analysis": {
                "high": {"total_trades": 82, "win_rate": 78.2, "avg_return": 4.1, "total_profit": 75420000, "profit_formatted": "Rp 75.42M"},
                "medium": {"total_trades": 115, "win_rate": 65.8, "avg_return": 2.8, "total_profit": 85230000, "profit_formatted": "Rp 85.23M"},
                "low": {"total_trades": 48, "win_rate": 58.3, "avg_return": 1.2, "total_profit": 24770000, "profit_formatted": "Rp 24.77M"}
            },
            "best_trades": [
                {"stock_code": "BBCA.JK", "profit": 24580000, "return_pct": 8.9, "confidence": 0.89, "date": "2024-08-15"},
                {"stock_code": "ASII.JK", "profit": 18920000, "return_pct": 7.2, "confidence": 0.82, "date": "2024-07-22"},
                {"stock_code": "UNVR.JK", "profit": 16450000, "return_pct": 6.8, "confidence": 0.91, "date": "2024-06-10"},
                {"stock_code": "BBRI.JK", "profit": 14230000, "return_pct": 5.9, "confidence": 0.76, "date": "2024-09-03"},
                {"stock_code": "TLKM.JK", "profit": 12880000, "return_pct": 5.4, "confidence": 0.71, "date": "2024-05-28"}
            ],
            "worst_trades": [
                {"stock_code": "JSMR.JK", "profit": -8920000, "return_pct": -4.2, "confidence": 0.65, "date": "2024-04-18"},
                {"stock_code": "PGAS.JK", "profit": -7560000, "return_pct": -3.8, "confidence": 0.58, "date": "2024-03-25"},
                {"stock_code": "ANTM.JK", "profit": -6890000, "return_pct": -3.1, "confidence": 0.62, "date": "2024-02-14"},
                {"stock_code": "ADRO.JK", "profit": -5420000, "return_pct": -2.9, "confidence": 0.59, "date": "2024-08-07"},
                {"stock_code": "ITMG.JK", "profit": -4780000, "return_pct": -2.3, "confidence": 0.67, "date": "2024-01-30"}
            ],
            "monthly_performance": [
                {"month": "Jan", "profit": 15420000, "trades": 21},
                {"month": "Feb", "profit": -8920000, "trades": 19},
                {"month": "Mar", "profit": 18650000, "trades": 23},
                {"month": "Apr", "profit": 12340000, "trades": 20},
                {"month": "May", "profit": -4580000, "trades": 18},
                {"month": "Jun", "profit": 22110000, "trades": 25},
                {"month": "Jul", "profit": 9870000, "trades": 22},
                {"month": "Aug", "profit": 16780000, "trades": 24},
                {"month": "Sep", "profit": 28920000, "trades": 27},
                {"month": "Oct", "profit": 7650000, "trades": 19},
                {"month": "Nov", "profit": 19340000, "trades": 23},
                {"month": "Dec", "profit": 21450000, "trades": 24}
            ],
            "period_start": "2023-01-01",
            "period_end": "2024-09-27",
            "generated_at": datetime.now().isoformat()
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)