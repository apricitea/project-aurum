"""
Demo FastAPI server for Project Aurum - Minimal setup for testing login
"""

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional, List
import hashlib
import json
import asyncio

# Initialize FastAPI
app = FastAPI(title="Project Aurum - Indonesian Quantitative Trading System")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:3003",
        "http://localhost:3004",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Security
SECRET_KEY = "demo-secret-key"
security = HTTPBearer()

# Models
class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user: dict

class User(BaseModel):
    id: int
    username: str
    email: str
    role: str

# Simple password hashing
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hash_password(plain_password) == hashed_password

# Mock user database
USERS_DB = {
    "admin": {
        "id": 1,
        "username": "admin",
        "email": "admin@projectaurum.com",
        "role": "admin",
        "hashed_password": hash_password("admin123")
    },
    "trader": {
        "id": 2,
        "username": "trader",
        "email": "trader@projectaurum.com",
        "role": "trader",
        "hashed_password": hash_password("trader123")
    }
}

def authenticate_user(username: str, password: str):
    user = USERS_DB.get(username)
    if not user or not verify_password(password, user["hashed_password"]):
        return False
    return user

def create_access_token(data: dict):
    # Simple token (not secure, for demo only)
    import base64
    import json
    token_data = {**data, "exp": (datetime.utcnow() + timedelta(hours=24)).isoformat()}
    return base64.b64encode(json.dumps(token_data).encode()).decode()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        import base64
        import json
        token_data = json.loads(base64.b64decode(credentials.credentials).decode())
        username = token_data.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = USERS_DB.get(username)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# Routes
@app.get("/")
async def root():
    return {"message": "Project Aurum - Indonesian Quantitative Trading System"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "Project Aurum API"
    }

@app.post("/auth/login", response_model=TokenResponse)
async def login(login_request: LoginRequest):
    user = authenticate_user(login_request.username, login_request.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user["username"]})

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=24 * 60 * 60,  # 24 hours
        user={
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "role": user["role"]
        }
    )

@app.get("/auth/me", response_model=User)
async def get_me(current_user: dict = Depends(get_current_user)):
    return User(
        id=current_user["id"],
        username=current_user["username"],
        email=current_user["email"],
        role=current_user["role"]
    )

@app.get("/signals/daily")
async def get_daily_signals(current_user: dict = Depends(get_current_user)):
    from indonesian_stocks_data import indonesian_data
    import random

    # Get accurate Indonesian stock data
    indonesian_stocks = indonesian_data.get_all_stocks()

    # Generate signals for random selection of stocks
    selected_stocks = random.sample(indonesian_stocks, 15)
    signals = []

    signal_types = ["BUY", "SELL", "HOLD"]

    for stock in selected_stocks:
        signal_type = random.choice(signal_types)
        confidence = round(random.uniform(0.6, 0.95), 2)

        # Use real current price with small variation
        current_price = indonesian_data.get_current_price(stock["code"])

        signals.append({
            "id": len(signals) + 1,
            "date": datetime.now().date().isoformat(),
            "stock_code": stock["code"],
            "sector": stock["sector"],
            "signal_type": signal_type,
            "composite_score": round(random.uniform(0.6, 0.95), 2),
            "confidence": confidence,
            "position_size": round(random.uniform(0.02, 0.05), 3),
            "current_price": current_price,
            "volume": random.randint(100000, 1000000),
            "technical_score": round(random.uniform(0.5, 0.9), 2),
            "fundamental_score": round(random.uniform(0.5, 0.9), 2),
            "sentiment_score": round(random.uniform(0.5, 0.9), 2),
            "risk_adjusted": True,
            "metadata": {
                "target_price": int(current_price * (1.1 if signal_type == "BUY" else 0.9 if signal_type == "SELL" else 1.0)),
                "stop_loss": int(current_price * (0.92 if signal_type == "BUY" else 1.08 if signal_type == "SELL" else 0.95)),
                "reasoning": f"Technical analysis and sector momentum for {stock['sector']} sector"
            },
            "generated_at": datetime.now().isoformat()
        })

    return {
        "date": datetime.now().date().isoformat(),
        "signals": signals,
        "generated_at": datetime.now().isoformat(),
        "total_signals": len(signals),
        "universe_size": len(indonesian_stocks),
        "market_summary": {
            "jci": 7234.56,
            "jci_change": 0.85,
            "market_status": "OPEN"
        }
    }

@app.get("/portfolio/summary")
async def get_portfolio_summary(current_user: dict = Depends(get_current_user)):
    return {
        "total_positions": 8,
        "total_market_value": 150000000,
        "total_cost_basis": 125000000,
        "total_unrealized_pnl": 2500000,
        "total_unrealized_pnl_percent": 1.67,
        "sector_breakdown": {
            "Banking": 35.5,
            "Telecommunications": 18.2,
            "Consumer Goods": 15.8,
            "Mining": 12.1,
            "Automotive": 10.4,
            "Property": 8.0
        },
        "cash_available": 25000000,
        "portfolio_beta": 1.12,
        "sharpe_ratio": 1.45,
        "max_drawdown": -0.08,
        "last_updated": datetime.now().isoformat()
    }

@app.get("/portfolio/positions")
async def get_positions(current_user: dict = Depends(get_current_user)):
    from indonesian_stocks_data import indonesian_data

    # Get current Indonesian stock prices for accurate data
    return [
        {
            "id": 1,
            "stock_code": "BBCA",
            "company_name": "Bank Central Asia Tbk",
            "quantity": 1000,
            "average_price": 9200,
            "current_price": indonesian_data.get_current_price("BBCA"),
            "market_value": indonesian_data.get_current_price("BBCA") * 1000,
            "unrealized_pnl": (indonesian_data.get_current_price("BBCA") - 9200) * 1000,
            "unrealized_pnl_percent": ((indonesian_data.get_current_price("BBCA") - 9200) / 9200) * 100,
            "sector": "Banking",
            "last_updated": datetime.now().isoformat()
        },
        {
            "id": 2,
            "stock_code": "TLKM",
            "company_name": "Telkom Indonesia Tbk",
            "quantity": 2000,
            "average_price": 3800,
            "current_price": indonesian_data.get_current_price("TLKM"),
            "market_value": indonesian_data.get_current_price("TLKM") * 2000,
            "unrealized_pnl": (indonesian_data.get_current_price("TLKM") - 3800) * 2000,
            "unrealized_pnl_percent": ((indonesian_data.get_current_price("TLKM") - 3800) / 3800) * 100,
            "sector": "Telecommunications",
            "last_updated": datetime.now().isoformat()
        },
        {
            "id": 3,
            "stock_code": "ASII",
            "company_name": "Astra International Tbk",
            "quantity": 500,
            "average_price": 6200,
            "current_price": indonesian_data.get_current_price("ASII"),
            "market_value": indonesian_data.get_current_price("ASII") * 500,
            "unrealized_pnl": (indonesian_data.get_current_price("ASII") - 6200) * 500,
            "unrealized_pnl_percent": ((indonesian_data.get_current_price("ASII") - 6200) / 6200) * 100,
            "sector": "Automotive",
            "last_updated": datetime.now().isoformat()
        },
        {
            "id": 4,
            "stock_code": "UNVR",
            "company_name": "Unilever Indonesia Tbk",
            "quantity": 1500,
            "average_price": 2500,
            "current_price": indonesian_data.get_current_price("UNVR"),
            "market_value": indonesian_data.get_current_price("UNVR") * 1500,
            "unrealized_pnl": (indonesian_data.get_current_price("UNVR") - 2500) * 1500,
            "unrealized_pnl_percent": ((indonesian_data.get_current_price("UNVR") - 2500) / 2500) * 100,
            "sector": "Consumer Goods",
            "last_updated": datetime.now().isoformat()
        },
        {
            "id": 5,
            "stock_code": "ITMG",
            "company_name": "Indo Tambangraya Megah Tbk",
            "quantity": 100,
            "average_price": 18000,
            "current_price": indonesian_data.get_current_price("ITMG"),
            "market_value": indonesian_data.get_current_price("ITMG") * 100,
            "unrealized_pnl": (indonesian_data.get_current_price("ITMG") - 18000) * 100,
            "unrealized_pnl_percent": ((indonesian_data.get_current_price("ITMG") - 18000) / 18000) * 100,
            "sector": "Mining",
            "last_updated": datetime.now().isoformat()
        },
        {
            "id": 6,
            "stock_code": "ICBP",
            "company_name": "Indofood CBP Sukses Makmur Tbk",
            "quantity": 800,
            "average_price": 10200,
            "current_price": indonesian_data.get_current_price("ICBP"),
            "market_value": indonesian_data.get_current_price("ICBP") * 800,
            "unrealized_pnl": (indonesian_data.get_current_price("ICBP") - 10200) * 800,
            "unrealized_pnl_percent": ((indonesian_data.get_current_price("ICBP") - 10200) / 10200) * 100,
            "sector": "Food & Beverages",
            "last_updated": datetime.now().isoformat()
        },
        {
            "id": 7,
            "stock_code": "SMGR",
            "company_name": "Semen Indonesia Tbk",
            "quantity": 1200,
            "average_price": 4900,
            "current_price": indonesian_data.get_current_price("SMGR"),
            "market_value": indonesian_data.get_current_price("SMGR") * 1200,
            "unrealized_pnl": (indonesian_data.get_current_price("SMGR") - 4900) * 1200,
            "unrealized_pnl_percent": ((indonesian_data.get_current_price("SMGR") - 4900) / 4900) * 100,
            "sector": "Cement",
            "last_updated": datetime.now().isoformat()
        },
        {
            "id": 8,
            "stock_code": "KLBF",
            "company_name": "Kalbe Farma Tbk",
            "quantity": 5000,
            "average_price": 1400,
            "current_price": indonesian_data.get_current_price("KLBF"),
            "market_value": indonesian_data.get_current_price("KLBF") * 5000,
            "unrealized_pnl": (indonesian_data.get_current_price("KLBF") - 1400) * 5000,
            "unrealized_pnl_percent": ((indonesian_data.get_current_price("KLBF") - 1400) / 1400) * 100,
            "sector": "Pharmaceuticals",
            "last_updated": datetime.now().isoformat()
        },
        {
            "id": 9,
            "stock_code": "PGAS",
            "company_name": "Perusahaan Gas Negara Tbk",
            "quantity": 3000,
            "average_price": 1350,
            "current_price": indonesian_data.get_current_price("PGAS"),
            "market_value": indonesian_data.get_current_price("PGAS") * 3000,
            "unrealized_pnl": (indonesian_data.get_current_price("PGAS") - 1350) * 3000,
            "unrealized_pnl_percent": ((indonesian_data.get_current_price("PGAS") - 1350) / 1350) * 100,
            "sector": "Energy",
            "last_updated": datetime.now().isoformat()
        },
        {
            "id": 10,
            "stock_code": "CPIN",
            "company_name": "Charoen Pokphand Indonesia Tbk",
            "quantity": 700,
            "average_price": 4200,
            "current_price": indonesian_data.get_current_price("CPIN"),
            "market_value": indonesian_data.get_current_price("CPIN") * 700,
            "unrealized_pnl": (indonesian_data.get_current_price("CPIN") - 4200) * 700,
            "unrealized_pnl_percent": ((indonesian_data.get_current_price("CPIN") - 4200) / 4200) * 100,
            "sector": "Agriculture",
            "last_updated": datetime.now().isoformat()
        }
    ]

@app.get("/alerts")
async def get_alerts(limit: int = 20, status: str = "active", current_user: dict = Depends(get_current_user)):
    return [
        {
            "id": 1,
            "type": "price_alert",
            "title": "BBCA.JK Price Target Reached",
            "message": "BBCA.JK has reached your price target of Rp 9,750",
            "severity": "info",
            "stock_code": "BBCA.JK",
            "trigger_price": 9750,
            "current_price": 9750,
            "created_at": datetime.now().isoformat(),
            "status": "active"
        },
        {
            "id": 2,
            "type": "risk_alert",
            "title": "Portfolio Risk Level High",
            "message": "Your portfolio concentration in Banking sector exceeds 40%",
            "severity": "warning",
            "created_at": (datetime.now() - timedelta(hours=2)).isoformat(),
            "status": "active"
        },
        {
            "id": 3,
            "type": "signal_alert",
            "title": "New BUY Signal: UNVR.JK",
            "message": "AI model generated BUY signal for Unilever Indonesia with 78% confidence",
            "severity": "info",
            "stock_code": "UNVR.JK",
            "confidence": 0.78,
            "created_at": (datetime.now() - timedelta(hours=1)).isoformat(),
            "status": "active"
        }
    ]

@app.get("/risk/overview")
async def get_risk_overview(current_user: dict = Depends(get_current_user)):
    return {
        "var_1day": 2500000,
        "var_1day_percent": 1.67,
        "beta": 1.15,
        "sharpe_ratio": 1.85,
        "max_drawdown": 8.5,
        "volatility": 18.2,
        "sector_concentration": {
            "Banking": 42.5,
            "Telecommunications": 18.3,
            "Consumer Goods": 15.2,
            "Mining": 12.0,
            "Others": 12.0
        },
        "risk_score": 6.8,
        "risk_level": "Medium-High"
    }

@app.get("/market/status")
async def get_market_status(current_user: dict = Depends(get_current_user)):
    return {
        "market_open": True,
        "session": "Regular Trading",
        "timezone": "Asia/Jakarta",
        "last_updated": datetime.now().isoformat(),
        "indices": {
            "JCI": {
                "value": 7234.56,
                "change": 62.15,
                "change_percent": 0.87
            },
            "LQ45": {
                "value": 985.23,
                "change": 8.45,
                "change_percent": 0.86
            },
            "Kompas100": {
                "value": 1234.67,
                "change": 10.23,
                "change_percent": 0.83
            }
        },
        "trading_hours": {
            "pre_open": "08:45-09:00",
            "session_1": "09:00-12:00",
            "break": "12:00-13:30",
            "session_2": "13:30-15:49",
            "post_close": "15:50-16:00"
        }
    }

@app.get("/analytics/performance")
async def get_performance_analytics(days: int = 30, current_user: dict = Depends(get_current_user)):
    return {
        "period_days": days,
        "total_return": 8.5,
        "annualized_return": 12.3,
        "volatility": 15.2,
        "sharpe_ratio": 1.85,
        "max_drawdown": 8.5,
        "win_rate": 68.5,
        "profit_factor": 1.45,
        "daily_returns": [
            {"date": (datetime.now() - timedelta(days=i)).date().isoformat(), "return": 0.5 + (i % 3) * 0.3}
            for i in range(days)
        ],
        "monthly_performance": [
            {"month": "2024-01", "return": 2.1},
            {"month": "2024-02", "return": 1.8},
            {"month": "2024-03", "return": 3.2},
            {"month": "2024-04", "return": -0.5},
            {"month": "2024-05", "return": 2.7}
        ],
        "top_performers": [
            {"stock_code": "BBCA.JK", "return": 12.5},
            {"stock_code": "TLKM.JK", "return": 8.9},
            {"stock_code": "ASII.JK", "return": 6.2}
        ]
    }

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Remove disconnected connections
                if connection in self.active_connections:
                    self.active_connections.remove(connection)

manager = ConnectionManager()

@app.websocket("/ws/alerts")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Send sample alert data every 30 seconds
            await asyncio.sleep(30)

            sample_alert = {
                "type": "market_alert",
                "timestamp": datetime.now().isoformat(),
                "message": "LQ45 index movement detected",
                "data": {
                    "index": "LQ45",
                    "value": 985.23,
                    "change": 8.45,
                    "change_percent": 0.86
                }
            }

            await manager.send_personal_message(json.dumps(sample_alert), websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        manager.disconnect(websocket)

# Backtesting endpoints
@app.get("/backtesting/performance")
async def get_backtesting_performance(current_user: dict = Depends(get_current_user)):
    """Get comprehensive backtesting performance analysis"""
    from backtesting_engine import backtest_engine

    # Run backtesting analysis
    performance_data = backtest_engine.run_backtest()

    return {
        "status": "success",
        "analysis_date": datetime.now().isoformat(),
        "performance": performance_data
    }

@app.get("/backtesting/confidence-analysis")
async def get_confidence_analysis(current_user: dict = Depends(get_current_user)):
    """Get confidence-based performance breakdown"""
    from backtesting_engine import backtest_engine

    if not backtest_engine.trades:
        backtest_engine.run_backtest()

    performance_data = backtest_engine.analyze_performance()

    return {
        "status": "success",
        "confidence_analysis": performance_data.get("confidence_analysis", {}),
        "overview": performance_data.get("overview", {})
    }

@app.get("/backtesting/sector-performance")
async def get_sector_performance(current_user: dict = Depends(get_current_user)):
    """Get sector-based performance analysis"""
    from backtesting_engine import backtest_engine

    if not backtest_engine.trades:
        backtest_engine.run_backtest()

    performance_data = backtest_engine.analyze_performance()

    return {
        "status": "success",
        "sector_analysis": performance_data.get("sector_analysis", {}),
        "monthly_performance": performance_data.get("monthly_performance", [])
    }

@app.get("/backtesting/best-worst-trades")
async def get_best_worst_trades(current_user: dict = Depends(get_current_user)):
    """Get best and worst performing trades"""
    from backtesting_engine import backtest_engine

    if not backtest_engine.trades:
        backtest_engine.run_backtest()

    performance_data = backtest_engine.analyze_performance()

    return {
        "status": "success",
        "best_trades": performance_data.get("best_trades", []),
        "worst_trades": performance_data.get("worst_trades", [])
    }

if __name__ == "__main__":
    import uvicorn
    print("Starting Project Aurum Demo API...")
    print("Frontend login credentials:")
    print("Username: admin, Password: admin123")
    print("Username: trader, Password: trader123")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)