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
    # Extended Indonesian stock universe beyond LQ45
    indonesian_stocks = [
        {"code": "BBCA", "name": "Bank Central Asia Tbk", "sector": "Banking", "price": 9750},
        {"code": "BMRI", "name": "Bank Mandiri Tbk", "sector": "Banking", "price": 5425},
        {"code": "BBRI", "name": "Bank Rakyat Indonesia Tbk", "sector": "Banking", "price": 4680},
        {"code": "BBNI", "name": "Bank Negara Indonesia Tbk", "sector": "Banking", "price": 8100},
        {"code": "ASII", "name": "Astra International Tbk", "sector": "Automotive", "price": 6500},
        {"code": "UNVR", "name": "Unilever Indonesia Tbk", "sector": "Consumer Goods", "price": 2680},
        {"code": "TLKM", "name": "Telkom Indonesia Tbk", "sector": "Telecommunications", "price": 4100},
        {"code": "INDF", "name": "Indofood Sukses Makmur Tbk", "sector": "Food & Beverages", "price": 6925},
        {"code": "ICBP", "name": "Indofood CBP Sukses Makmur Tbk", "sector": "Food & Beverages", "price": 10950},
        {"code": "KLBF", "name": "Kalbe Farma Tbk", "sector": "Pharmaceuticals", "price": 1535},
        {"code": "GGRM", "name": "Gudang Garam Tbk", "sector": "Tobacco", "price": 32000},
        {"code": "HMSP", "name": "HM Sampoerna Tbk", "sector": "Tobacco", "price": 1385},
        {"code": "ITMG", "name": "Indo Tambangraya Megah Tbk", "sector": "Mining", "price": 19525},
        {"code": "PTBA", "name": "Bukit Asam Tbk", "sector": "Mining", "price": 3090},
        {"code": "ADRO", "name": "Adaro Energy Tbk", "sector": "Mining", "price": 2970},
        {"code": "ANTM", "name": "Aneka Tambang Tbk", "sector": "Mining", "price": 1720},
        {"code": "INCO", "name": "Vale Indonesia Tbk", "sector": "Mining", "price": 4280},
        {"code": "SMGR", "name": "Semen Indonesia Tbk", "sector": "Cement", "price": 5150},
        {"code": "INTP", "name": "Indocement Tunggal Prakarsa Tbk", "sector": "Cement", "price": 10100},
        {"code": "WIKA", "name": "Wijaya Karya Tbk", "sector": "Construction", "price": 1345},
        {"code": "PTPP", "name": "PP (Persero) Tbk", "sector": "Construction", "price": 1105},
        {"code": "WSKT", "name": "Waskita Karya Tbk", "sector": "Construction", "price": 895},
        {"code": "ADHI", "name": "Adhi Karya Tbk", "sector": "Construction", "price": 1020},
        {"code": "JSMR", "name": "Jasa Marga Tbk", "sector": "Infrastructure", "price": 4100},
        {"code": "PGAS", "name": "Perusahaan Gas Negara Tbk", "sector": "Energy", "price": 1485},
        {"code": "PGEO", "name": "Perusahaan Gas Negara Tbk", "sector": "Energy", "price": 675},
        {"code": "MEDC", "name": "Medco Energi Internasional Tbk", "sector": "Energy", "price": 1135},
        {"code": "AKRA", "name": "AKR Corporindo Tbk", "sector": "Energy", "price": 3800},
        {"code": "CPIN", "name": "Charoen Pokphand Indonesia Tbk", "sector": "Agriculture", "price": 4690},
        {"code": "JPFA", "name": "Japfa Comfeed Indonesia Tbk", "sector": "Agriculture", "price": 1150},
        {"code": "SIDO", "name": "Industri Jamu dan Farmasi Sido Muncul Tbk", "sector": "Pharmaceuticals", "price": 565},
        {"code": "KAEF", "name": "Kimia Farma Tbk", "sector": "Pharmaceuticals", "price": 1895},
        {"code": "DVLA", "name": "Darya-Varia Laboratoria Tbk", "sector": "Pharmaceuticals", "price": 1980},
        {"code": "MAPI", "name": "Mitra Adiperkasa Tbk", "sector": "Retail", "price": 2020},
        {"code": "LPPF", "name": "Matahari Department Store Tbk", "sector": "Retail", "price": 465},
        {"code": "ERAA", "name": "Erajaya Swasembada Tbk", "sector": "Retail", "price": 1315},
        {"code": "ACES", "name": "Ace Hardware Indonesia Tbk", "sector": "Retail", "price": 775},
        {"code": "SCMA", "name": "Surya Citra Media Tbk", "sector": "Media", "price": 1410},
        {"code": "VIVA", "name": "Visi Media Asia Tbk", "sector": "Media", "price": 156},
        {"code": "EMTK", "name": "Elang Mahkota Teknologi Tbk", "sector": "Media", "price": 1600},
        {"code": "ISAT", "name": "Indosat Ooredoo Hutchison Tbk", "sector": "Telecommunications", "price": 5275},
        {"code": "EXCL", "name": "XL Axiata Tbk", "sector": "Telecommunications", "price": 2410},
        {"code": "FREN", "name": "Smartfren Telecom Tbk", "sector": "Telecommunications", "price": 590},
        {"code": "BKSL", "name": "Sentul City Tbk", "sector": "Property", "price": 76},
        {"code": "LPKR", "name": "Lippo Karawaci Tbk", "sector": "Property", "price": 294},
        {"code": "PWON", "name": "Pakuwon Jati Tbk", "sector": "Property", "price": 600},
        {"code": "CTRA", "name": "Ciputra Development Tbk", "sector": "Property", "price": 1115},
        {"code": "PLIN", "name": "Plaza Indonesia Realty Tbk", "sector": "Property", "price": 1270},
        {"code": "MDLN", "name": "Modernland Realty Tbk", "sector": "Property", "price": 680},
        {"code": "APLN", "name": "Agung Podomoro Land Tbk", "sector": "Property", "price": 214},
        {"code": "DILD", "name": "Intiland Development Tbk", "sector": "Property", "price": 480},
        {"code": "BCAP", "name": "MNC Kapital Indonesia Tbk", "sector": "Finance", "price": 76},
        {"code": "BMTR", "name": "Global Mediacom Tbk", "sector": "Finance", "price": 1110},
        {"code": "PNBS", "name": "Bank Panin Dubai Syariah Tbk", "sector": "Banking", "price": 206},
        {"code": "NISP", "name": "Bank OCBC NISP Tbk", "sector": "Banking", "price": 1015},
        {"code": "MAYA", "name": "Bank Mayapada Internasional Tbk", "sector": "Banking", "price": 2400},
        {"code": "MEGA", "name": "Bank Mega Tbk", "sector": "Banking", "price": 3780},
        {"code": "BNBA", "name": "Bank Bumi Arta Tbk", "sector": "Banking", "price": 196},
        {"code": "BJBR", "name": "Bank Jabar Banten Tbk", "sector": "Banking", "price": 1580},
        {"code": "BSDE", "name": "Bumi Serpong Damai Tbk", "sector": "Property", "price": 1055},
        {"code": "PPRO", "name": "PP Properti Tbk", "sector": "Property", "price": 168},
        {"code": "RALS", "name": "Ramayana Lestari Sentosa Tbk", "sector": "Retail", "price": 810},
        {"code": "HERO", "name": "Hero Supermarket Tbk", "sector": "Retail", "price": 102}
    ]

    import random

    # Generate signals for random selection of stocks
    selected_stocks = random.sample(indonesian_stocks, 15)
    signals = []

    signal_types = ["BUY", "SELL", "HOLD"]

    for stock in selected_stocks:
        signal_type = random.choice(signal_types)
        confidence = round(random.uniform(0.6, 0.95), 2)
        price_variation = random.uniform(0.95, 1.05)

        signals.append({
            "stock_code": stock["code"],
            "company_name": stock["name"],
            "signal": signal_type,
            "confidence": confidence,
            "current_price": int(stock["price"] * price_variation),
            "target_price": int(stock["price"] * (1.1 if signal_type == "BUY" else 0.9 if signal_type == "SELL" else 1.0)),
            "stop_loss": int(stock["price"] * (0.92 if signal_type == "BUY" else 1.08 if signal_type == "SELL" else 0.95)),
            "reasoning": f"Technical analysis and sector momentum for {stock['sector']} sector",
            "sector": stock["sector"],
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
    return [
        {
            "id": 1,
            "stock_code": "BBCA",
            "company_name": "Bank Central Asia Tbk",
            "shares": 1000,
            "average_price": 9200,
            "current_price": 9750,
            "market_value": 9750000,
            "pnl": 550000,
            "pnl_percent": 5.98,
            "sector": "Banking"
        },
        {
            "id": 2,
            "stock_code": "TLKM",
            "company_name": "Telkom Indonesia Tbk",
            "shares": 2000,
            "average_price": 3800,
            "current_price": 4100,
            "market_value": 8200000,
            "pnl": 600000,
            "pnl_percent": 7.89,
            "sector": "Telecommunications"
        },
        {
            "id": 3,
            "stock_code": "ASII",
            "company_name": "Astra International Tbk",
            "shares": 500,
            "average_price": 6200,
            "current_price": 6500,
            "market_value": 3250000,
            "pnl": 150000,
            "pnl_percent": 4.84,
            "sector": "Automotive"
        },
        {
            "id": 4,
            "stock_code": "UNVR",
            "company_name": "Unilever Indonesia Tbk",
            "shares": 1500,
            "average_price": 2500,
            "current_price": 2680,
            "market_value": 4020000,
            "pnl": 270000,
            "pnl_percent": 7.20,
            "sector": "Consumer Goods"
        },
        {
            "id": 5,
            "stock_code": "ITMG",
            "company_name": "Indo Tambangraya Megah Tbk",
            "shares": 100,
            "average_price": 18000,
            "current_price": 19525,
            "market_value": 1952500,
            "pnl": 152500,
            "pnl_percent": 8.47,
            "sector": "Mining"
        },
        {
            "id": 6,
            "stock_code": "ICBP",
            "company_name": "Indofood CBP Sukses Makmur Tbk",
            "shares": 800,
            "average_price": 10200,
            "current_price": 10950,
            "market_value": 8760000,
            "pnl": 600000,
            "pnl_percent": 7.35,
            "sector": "Food & Beverages"
        },
        {
            "id": 7,
            "stock_code": "SMGR",
            "company_name": "Semen Indonesia Tbk",
            "shares": 1200,
            "average_price": 4900,
            "current_price": 5150,
            "market_value": 6180000,
            "pnl": 300000,
            "pnl_percent": 5.10,
            "sector": "Cement"
        },
        {
            "id": 8,
            "stock_code": "KLBF",
            "company_name": "Kalbe Farma Tbk",
            "shares": 5000,
            "average_price": 1400,
            "current_price": 1535,
            "market_value": 7675000,
            "pnl": 675000,
            "pnl_percent": 9.64,
            "sector": "Pharmaceuticals"
        },
        {
            "id": 9,
            "stock_code": "PGAS",
            "company_name": "Perusahaan Gas Negara Tbk",
            "shares": 3000,
            "average_price": 1350,
            "current_price": 1485,
            "market_value": 4455000,
            "pnl": 405000,
            "pnl_percent": 10.00,
            "sector": "Energy"
        },
        {
            "id": 10,
            "stock_code": "CPIN",
            "company_name": "Charoen Pokphand Indonesia Tbk",
            "shares": 700,
            "average_price": 4200,
            "current_price": 4690,
            "market_value": 3283000,
            "pnl": 343000,
            "pnl_percent": 11.67,
            "sector": "Agriculture"
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

if __name__ == "__main__":
    import uvicorn
    print("Starting Project Aurum Demo API...")
    print("Frontend login credentials:")
    print("Username: admin, Password: admin123")
    print("Username: trader, Password: trader123")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)