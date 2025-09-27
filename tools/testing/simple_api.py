"""
Simple FastAPI server for Project Aurum - Quick development setup
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional
import jwt
from passlib.context import CryptContext

# Initialize FastAPI
app = FastAPI(title="Project Aurum - Indonesian Quantitative Trading System")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
SECRET_KEY = "your-super-secret-jwt-key-change-this-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
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

# Mock user database
USERS_DB = {
    "admin": {
        "id": 1,
        "username": "admin",
        "email": "admin@projectaurum.com",
        "role": "admin",
        "hashed_password": pwd_context.hash("admin123")
    },
    "trader": {
        "id": 2,
        "username": "trader",
        "email": "trader@projectaurum.com",
        "role": "trader",
        "hashed_password": pwd_context.hash("trader123")
    }
}

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def authenticate_user(username: str, password: str):
    user = USERS_DB.get(username)
    if not user or not verify_password(password, user["hashed_password"]):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

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

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
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
    # Mock signal data
    return {
        "date": datetime.now().date().isoformat(),
        "signals": [
            {
                "stock_code": "BBCA.JK",
                "company_name": "Bank Central Asia Tbk",
                "signal": "BUY",
                "confidence": 0.85,
                "current_price": 9750,
                "target_price": 10500,
                "stop_loss": 9200,
                "reasoning": "Strong Q3 earnings, positive technical indicators"
            },
            {
                "stock_code": "BMRI.JK",
                "company_name": "Bank Mandiri Tbk",
                "signal": "HOLD",
                "confidence": 0.65,
                "current_price": 5425,
                "target_price": 5800,
                "stop_loss": 5000,
                "reasoning": "Consolidation phase, wait for breakout"
            }
        ],
        "market_summary": {
            "jci": 7234.56,
            "jci_change": 0.85,
            "market_status": "OPEN"
        }
    }

@app.get("/portfolio/summary")
async def get_portfolio_summary(current_user: dict = Depends(get_current_user)):
    return {
        "total_value": 150000000,  # 150M IDR
        "cash": 25000000,          # 25M IDR
        "invested": 125000000,     # 125M IDR
        "daily_pnl": 2500000,      # 2.5M IDR
        "daily_pnl_percent": 1.67,
        "total_pnl": 15000000,     # 15M IDR
        "total_pnl_percent": 11.11,
        "positions_count": 8
    }

@app.get("/portfolio/positions")
async def get_positions(current_user: dict = Depends(get_current_user)):
    return [
        {
            "stock_code": "BBCA.JK",
            "company_name": "Bank Central Asia Tbk",
            "quantity": 1000,
            "avg_price": 9200,
            "current_price": 9750,
            "market_value": 9750000,
            "unrealized_pnl": 550000,
            "unrealized_pnl_percent": 5.98
        },
        {
            "stock_code": "BMRI.JK",
            "company_name": "Bank Mandiri Tbk",
            "quantity": 2000,
            "avg_price": 5100,
            "current_price": 5425,
            "market_value": 10850000,
            "unrealized_pnl": 650000,
            "unrealized_pnl_percent": 6.37
        }
    ]

@app.get("/market/status")
async def get_market_status():
    current_time = datetime.now()
    # Simple market hours check (9:00-15:49 WIB)
    market_open = current_time.replace(hour=9, minute=0, second=0)
    market_close = current_time.replace(hour=15, minute=49, second=0)

    is_open = market_open <= current_time <= market_close

    return {
        "status": "OPEN" if is_open else "CLOSED",
        "local_time": current_time.isoformat(),
        "timezone": "Asia/Jakarta",
        "next_open": market_open.isoformat() if not is_open else None,
        "next_close": market_close.isoformat() if is_open else None,
        "indices": {
            "JCI": {
                "value": 7234.56,
                "change": 62.34,
                "change_percent": 0.87
            },
            "LQ45": {
                "value": 985.23,
                "change": 8.45,
                "change_percent": 0.86
            }
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)