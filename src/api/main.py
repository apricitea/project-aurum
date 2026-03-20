"""
Main FastAPI Application for Indonesian Quantitative Trading Alert System
Provides REST API endpoints for alert management, portfolio tracking, and real-time monitoring
"""

from fastapi import FastAPI, HTTPException, Depends, Security, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

import asyncio
import uvicorn
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import logging
from contextlib import asynccontextmanager
import os

import pytz
from celery import Celery

from src.api.auth import AuthManager, get_current_user, User
from src.api.database import DatabaseManager, get_db, set_db_manager
from src.api.alert_engine import AlertEngine
from src.api.signal_service import SignalService
from src.api.risk_monitor import RiskMonitor
from src.api.schemas import *
from src.api.config import settings

# Celery app — defined at module level so it is accessible as src.api.main:celery_app
# for Celery worker/beat containers in docker-compose.prod.yml
celery_app = Celery(
    "project_aurum",
    broker=settings.get_redis_url(),
    backend=settings.get_redis_url(),
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Jakarta",
    enable_utc=True,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global services
alert_engine: AlertEngine = None
signal_service: SignalService = None
risk_monitor: RiskMonitor = None
db_manager: DatabaseManager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global alert_engine, signal_service, risk_monitor, db_manager

    # Startup
    logger.info("Starting Indonesian Quantitative Trading Alert System...")

    # Initialize database
    db_manager = DatabaseManager()
    await db_manager.initialize()
    set_db_manager(db_manager)  # register singleton for get_db() dependency

    # Initialize services
    alert_engine = AlertEngine(db_manager)
    signal_service = SignalService(db_manager)
    risk_monitor = RiskMonitor(db_manager)

    # Start background tasks
    await alert_engine.initialize()
    await risk_monitor.start_monitoring()

    logger.info("Alert system initialized successfully")

    yield

    # Shutdown
    logger.info("Shutting down alert system...")
    if risk_monitor:
        await risk_monitor.stop_monitoring()
    if db_manager:
        await db_manager.close()


# Initialize FastAPI app
app = FastAPI(
    title="Indonesian Quantitative Trading Alert System",
    description="Production-ready alert system for IDX quantitative trading",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# Security
security = HTTPBearer()
auth_manager = AuthManager()


# Health Check Endpoints
@app.get("/health", tags=["Health"])
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "alert-system",
        "version": "1.0.0"
    }


@app.get("/health/detailed", tags=["Health"])
async def detailed_health_check():
    """Detailed health check with service status"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {}
    }

    # Check database connection
    try:
        await db_manager.health_check()
        health_status["services"]["database"] = "healthy"
    except Exception as e:
        health_status["services"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"

    # Check alert engine
    if alert_engine and alert_engine.is_running:
        health_status["services"]["alert_engine"] = "healthy"
    else:
        health_status["services"]["alert_engine"] = "unhealthy"
        health_status["status"] = "degraded"

    # Check risk monitor
    if risk_monitor and risk_monitor.is_monitoring:
        health_status["services"]["risk_monitor"] = "healthy"
    else:
        health_status["services"]["risk_monitor"] = "unhealthy"
        health_status["status"] = "degraded"

    return health_status


# Authentication Endpoints
@app.post("/auth/login", response_model=TokenResponse, tags=["Authentication"])
async def login(credentials: LoginRequest):
    """Authenticate user and return access token"""
    try:
        token_data = await auth_manager.authenticate(
            credentials.username,
            credentials.password
        )
        return TokenResponse(**token_data)
    except Exception as e:
        logger.error(f"Login failed for {credentials.username}: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid credentials")


@app.post("/auth/refresh", response_model=TokenResponse, tags=["Authentication"])
async def refresh_token(token_request: RefreshTokenRequest):
    """Refresh access token using refresh token"""
    try:
        token_data = await auth_manager.refresh_token(token_request.refresh_token)
        return TokenResponse(**token_data)
    except Exception as e:
        logger.error(f"Token refresh failed: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid refresh token")


@app.get("/auth/me", response_model=UserProfile, tags=["Authentication"])
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile"""
    return UserProfile(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        role=current_user.role,
        permissions=current_user.permissions,
        created_at=current_user.created_at,
        last_login=current_user.last_login
    )


# Alert Management Endpoints
@app.get("/alerts", response_model=List[AlertResponse], tags=["Alerts"])
async def get_alerts(
    limit: int = 100,
    offset: int = 0,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user)
):
    """Get alerts with filtering and pagination"""
    try:
        alerts = await alert_engine.get_alerts(
            limit=limit,
            offset=offset,
            status=status,
            priority=priority,
            start_date=start_date,
            end_date=end_date,
            user_id=current_user.id
        )
        return [AlertResponse.from_db(alert) for alert in alerts]
    except Exception as e:
        logger.error(f"Failed to retrieve alerts: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve alerts")


@app.post("/alerts", response_model=AlertResponse, tags=["Alerts"])
async def create_alert(
    alert_request: CreateAlertRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """Create new alert"""
    try:
        alert = await alert_engine.create_alert(
            alert_type=alert_request.alert_type,
            message=alert_request.message,
            priority=alert_request.priority,
            metadata=alert_request.metadata,
            user_id=current_user.id
        )

        # Schedule alert delivery in background
        background_tasks.add_task(
            alert_engine.process_alert,
            alert.id
        )

        return AlertResponse.from_db(alert)
    except Exception as e:
        logger.error(f"Failed to create alert: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create alert")


@app.put("/alerts/{alert_id}/status", response_model=AlertResponse, tags=["Alerts"])
async def update_alert_status(
    alert_id: int,
    status_request: UpdateAlertStatusRequest,
    current_user: User = Depends(get_current_user)
):
    """Update alert status (acknowledge, dismiss, etc.)"""
    try:
        alert = await alert_engine.update_alert_status(
            alert_id=alert_id,
            status=status_request.status,
            notes=status_request.notes,
            user_id=current_user.id
        )
        return AlertResponse.from_db(alert)
    except Exception as e:
        logger.error(f"Failed to update alert status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update alert status")


# Signal Management Endpoints
@app.get("/signals/daily", response_model=DailySignalsResponse, tags=["Signals"])
async def get_daily_signals(
    date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user)
):
    """Get daily trading signals"""
    try:
        target_date = date or datetime.now().date()
        signals = await signal_service.get_daily_signals(target_date)

        return DailySignalsResponse(
            date=target_date,
            signals=signals,
            generated_at=signals[0].generated_at if signals else None,
            total_signals=len(signals)
        )
    except Exception as e:
        logger.error(f"Failed to retrieve daily signals: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve daily signals")


@app.post("/signals/generate", response_model=SignalGenerationResponse, tags=["Signals"])
async def generate_signals(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """Manually trigger signal generation"""
    if not current_user.has_permission("generate_signals"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        # Start signal generation in background
        task_id = await signal_service.start_signal_generation()

        return SignalGenerationResponse(
            task_id=task_id,
            status="started",
            message="Signal generation started",
            started_at=datetime.now()
        )
    except Exception as e:
        logger.error(f"Failed to start signal generation: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to start signal generation")


@app.get("/signals/generation/{task_id}", response_model=SignalGenerationStatus, tags=["Signals"])
async def get_signal_generation_status(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get signal generation task status"""
    try:
        status = await signal_service.get_generation_status(task_id)
        return SignalGenerationStatus(**status)
    except Exception as e:
        logger.error(f"Failed to get generation status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get generation status")


# Portfolio Management Endpoints
@app.get("/portfolio/summary", response_model=PortfolioSummaryResponse, tags=["Portfolio"])
async def get_portfolio_summary(
    current_user: User = Depends(get_current_user)
):
    """Get current portfolio summary"""
    try:
        summary = await signal_service.get_portfolio_summary()
        return PortfolioSummaryResponse(**summary)
    except Exception as e:
        logger.error(f"Failed to get portfolio summary: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get portfolio summary")


@app.get("/portfolio/positions", response_model=List[PositionResponse], tags=["Portfolio"])
async def get_current_positions(
    current_user: User = Depends(get_current_user)
):
    """Get current portfolio positions"""
    try:
        positions = await signal_service.get_current_positions()
        return [PositionResponse.from_db(pos) for pos in positions]
    except Exception as e:
        logger.error(f"Failed to get positions: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get positions")


@app.post("/portfolio/positions", response_model=PositionResponse, tags=["Portfolio"])
async def update_position(
    position_request: UpdatePositionRequest,
    current_user: User = Depends(get_current_user)
):
    """Update portfolio position"""
    if not current_user.has_permission("manage_portfolio"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        position = await signal_service.update_position(
            stock_code=position_request.stock_code,
            quantity=position_request.quantity,
            average_price=position_request.average_price,
            user_id=current_user.id
        )
        return PositionResponse.from_db(position)
    except Exception as e:
        logger.error(f"Failed to update position: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update position")


# Risk Monitoring Endpoints
@app.get("/risk/overview", response_model=RiskOverviewResponse, tags=["Risk Management"])
async def get_risk_overview(
    current_user: User = Depends(get_current_user)
):
    """Get current risk overview"""
    try:
        risk_data = await risk_monitor.get_risk_overview()
        return RiskOverviewResponse(**risk_data)
    except Exception as e:
        logger.error(f"Failed to get risk overview: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get risk overview")


@app.get("/risk/alerts", response_model=List[RiskAlertResponse], tags=["Risk Management"])
async def get_risk_alerts(
    active_only: bool = True,
    current_user: User = Depends(get_current_user)
):
    """Get risk alerts"""
    try:
        alerts = await risk_monitor.get_risk_alerts(active_only=active_only)
        return [RiskAlertResponse.from_db(alert) for alert in alerts]
    except Exception as e:
        logger.error(f"Failed to get risk alerts: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get risk alerts")


# Market Data Endpoints
@app.get("/market/status", response_model=MarketStatusResponse, tags=["Market Data"])
async def get_market_status():
    """Get current market status"""
    try:
        # Check if market is open (IDX hours: 09:00-15:49 WIB)
        wib = pytz.timezone("Asia/Jakarta")
        jakarta_time = datetime.now(wib)
        market_open = jakarta_time.time() >= datetime.strptime("09:00", "%H:%M").time()
        market_close = jakarta_time.time() <= datetime.strptime("15:49", "%H:%M").time()
        is_market_open = market_open and market_close and jakarta_time.weekday() < 5

        return MarketStatusResponse(
            is_open=is_market_open,
            current_time=jakarta_time,
            next_open=None,  # Calculate next market open time
            next_close=None,  # Calculate next market close time
            session_type="regular"  # regular, pre_market, after_hours
        )
    except Exception as e:
        logger.error(f"Failed to get market status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get market status")


# Analytics and Reporting Endpoints
@app.get("/analytics/performance", response_model=PerformanceAnalyticsResponse, tags=["Analytics"])
async def get_performance_analytics(
    days: int = 30,
    current_user: User = Depends(get_current_user)
):
    """Get performance analytics"""
    try:
        analytics = await signal_service.get_performance_analytics(days=days)
        return PerformanceAnalyticsResponse(**analytics)
    except Exception as e:
        logger.error(f"Failed to get performance analytics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get performance analytics")


@app.get("/reports/daily", tags=["Reports"])
async def generate_daily_report(
    date: Optional[datetime] = None,
    format: str = "json",
    current_user: User = Depends(get_current_user)
):
    """Generate daily trading report"""
    try:
        target_date = date or datetime.now().date()
        report = await signal_service.generate_daily_report(target_date, format)

        if format == "json":
            return report
        else:
            # Return file download for PDF/CSV formats
            return JSONResponse(
                content={"download_url": f"/downloads/daily_report_{target_date}.{format}"},
                headers={"Content-Type": "application/json"}
            )
    except Exception as e:
        logger.error(f"Failed to generate daily report: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate daily report")


# WebSocket for Real-time Updates
@app.websocket("/ws/alerts")
async def websocket_alerts(websocket):
    """WebSocket endpoint for real-time alert updates"""
    await websocket.accept()

    # Add client to alert notification list
    client_id = await alert_engine.add_websocket_client(websocket)

    try:
        while True:
            # Keep connection alive
            await asyncio.sleep(30)
            await websocket.ping()
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
    finally:
        # Remove client from notification list
        await alert_engine.remove_websocket_client(client_id)


# Custom OpenAPI documentation
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Indonesian Quantitative Trading Alert System",
        version="1.0.0",
        description="Comprehensive API for managing trading alerts, signals, and portfolio monitoring",
        routes=app.routes,
    )

    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "HTTPBearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# Development server
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        access_log=True
    )