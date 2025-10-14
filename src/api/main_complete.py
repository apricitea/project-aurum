"""
Complete FastAPI Application with All Dashboard Endpoints
Extends the main API with market data, analytics, and dashboard-specific endpoints
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
import logging
from contextlib import asynccontextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from .auth import get_current_user, User
from .database import DatabaseManager
from .database_extensions import StockMaster, DailyStockPrice
from .alert_engine import AlertEngine
from .signal_service import SignalService
from .risk_monitor import RiskMonitor
from .schemas import *
from .config import settings

# Import data integration service
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from data_pipeline.data_integration_service import DataIntegrationService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global services
alert_engine: AlertEngine = None
signal_service: SignalService = None
risk_monitor: RiskMonitor = None
db_manager: DatabaseManager = None

# Database session for data integration
engine = None
SessionLocal = None


def get_db_session():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global alert_engine, signal_service, risk_monitor, db_manager, engine, SessionLocal

    logger.info("Starting Indonesian Quantitative Trading System...")

    # Initialize database
    db_manager = DatabaseManager()
    await db_manager.initialize()

    # Create SQLAlchemy engine for data integration service
    try:
        db_url = (
            f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}"
            f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
        )
    except:
        db_url = "sqlite:///data/trading_system.db"

    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)

    # Initialize services
    alert_engine = AlertEngine(db_manager)
    signal_service = SignalService(db_manager)
    risk_monitor = RiskMonitor(db_manager)

    await alert_engine.initialize()
    await signal_service.initialize()
    await risk_monitor.start_monitoring()

    logger.info("All services initialized successfully")

    yield

    # Shutdown
    logger.info("Shutting down services...")
    if risk_monitor:
        await risk_monitor.stop_monitoring()
    if db_manager:
        await db_manager.close()


app = FastAPI(
    title="Indonesian Quantitative Trading System - Complete API",
    description="Full-featured API with market data, analytics, and dashboard endpoints",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS if hasattr(settings, 'ALLOWED_ORIGINS') else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)


# ============================================================================
# HEALTH & STATUS ENDPOINTS
# ============================================================================

@app.get("/health", tags=["Health"])
async def health_check():
    """Basic health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "trading-system",
        "version": "2.0.0"
    }


@app.get("/health/detailed", tags=["Health"])
async def detailed_health():
    """Detailed health check with all services"""
    health = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {}
    }

    try:
        db_healthy = await db_manager.health_check()
        health["services"]["database"] = "healthy" if db_healthy else "unhealthy"
    except:
        health["services"]["database"] = "unhealthy"
        health["status"] = "degraded"

    health["services"]["alert_engine"] = "healthy" if alert_engine and alert_engine.is_running else "unhealthy"
    health["services"]["signal_service"] = "healthy" if signal_service and signal_service.is_initialized else "unhealthy"
    health["services"]["risk_monitor"] = "healthy" if risk_monitor and risk_monitor.is_monitoring else "unhealthy"

    return health


# ============================================================================
# MARKET DATA ENDPOINTS
# ============================================================================

@app.get("/market/status", response_model=MarketStatusResponse, tags=["Market Data"])
async def get_market_status():
    """Get current market status (open/closed)"""
    import pytz

    jakarta_tz = pytz.timezone('Asia/Jakarta')
    current_time = datetime.now(jakarta_tz)

    # IDX trading hours: 09:00 - 16:00 WIB, Monday-Friday
    is_weekend = current_time.weekday() >= 5  # Saturday=5, Sunday=6
    trading_start = current_time.replace(hour=9, minute=0, second=0)
    trading_end = current_time.replace(hour=16, minute=0, second=0)

    is_trading_hours = trading_start <= current_time <= trading_end
    is_open = is_trading_hours and not is_weekend

    # Determine session type
    if is_weekend:
        session_type = "closed"
    elif current_time < trading_start:
        session_type = "pre_market"
    elif current_time > trading_end:
        session_type = "after_hours"
    else:
        session_type = "regular"

    return MarketStatusResponse(
        is_open=is_open,
        current_time=current_time,
        session_type=session_type
    )


@app.get("/market/snapshot", tags=["Market Data"])
async def get_market_snapshot(db: Session = Depends(get_db_session)):
    """Get current market snapshot with statistics"""
    integration_service = DataIntegrationService(db)
    snapshot = integration_service.get_market_snapshot()
    return snapshot


@app.get("/market/indices", tags=["Market Data"])
async def get_market_indices(db: Session = Depends(get_db_session)):
    """Get major market indices (JCI, LQ45, IDX30)"""
    # Calculate indices from component stocks
    try:
        # Get LQ45 stocks
        lq45_stocks = db.query(StockMaster).filter(
            StockMaster.is_lq45 == True,
            StockMaster.is_active == True
        ).all()

        lq45_codes = [s.stock_code for s in lq45_stocks]

        # Get latest prices for LQ45
        latest_date = db.query(func.max(DailyStockPrice.date)).scalar()

        if not latest_date:
            return {"error": "No price data available"}

        lq45_prices = db.query(DailyStockPrice).filter(
            and_(
                DailyStockPrice.stock_code.in_(lq45_codes),
                DailyStockPrice.date == latest_date
            )
        ).all()

        # Calculate simple average (in real system would use market cap weighted)
        lq45_avg_change = np.mean([p.price_change_percent for p in lq45_prices if p.price_change_percent])
        lq45_total_volume = sum([p.volume for p in lq45_prices if p.volume])

        # Get all stocks for JCI
        all_prices = db.query(DailyStockPrice).filter(
            DailyStockPrice.date == latest_date
        ).all()

        jci_avg_change = np.mean([p.price_change_percent for p in all_prices if p.price_change_percent])

        return {
            "indices": [
                {
                    "code": "JCI",
                    "name": "Jakarta Composite Index",
                    "value": 7125.45,  # Mock base value
                    "change": jci_avg_change * 71.25,  # Approximate change
                    "change_percent": jci_avg_change,
                    "volume": sum([p.volume for p in all_prices if p.volume])
                },
                {
                    "code": "LQ45",
                    "name": "LQ45 Index",
                    "value": 985.67,  # Mock base value
                    "change": lq45_avg_change * 9.86,
                    "change_percent": lq45_avg_change,
                    "volume": lq45_total_volume
                }
            ],
            "date": latest_date.isoformat(),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get market indices: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve market indices")


@app.get("/market/sectors", tags=["Market Data"])
async def get_sector_performance(
    days: int = 30,
    db: Session = Depends(get_db_session)
):
    """Get sector performance"""
    integration_service = DataIntegrationService(db)
    sector_perf = integration_service.get_sector_performance(days=days)
    return {"sectors": sector_perf, "period_days": days}


# ============================================================================
# PORTFOLIO ENDPOINTS
# ============================================================================

@app.get("/portfolio/summary", response_model=PortfolioSummaryResponse, tags=["Portfolio"])
async def get_portfolio_summary(current_user: User = Depends(get_current_user)):
    """Get portfolio summary with aggregated metrics"""
    try:
        summary = await signal_service.get_portfolio_summary()
        return PortfolioSummaryResponse(**summary)
    except Exception as e:
        logger.error(f"Failed to get portfolio summary: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve portfolio summary")


@app.get("/portfolio/positions", response_model=List[PositionResponse], tags=["Portfolio"])
async def get_portfolio_positions(current_user: User = Depends(get_current_user)):
    """Get all current portfolio positions"""
    try:
        positions = await signal_service.get_current_positions()
        return [PositionResponse.from_db(pos) for pos in positions]
    except Exception as e:
        logger.error(f"Failed to get positions: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve positions")


@app.put("/portfolio/positions/{stock_code}", response_model=PositionResponse, tags=["Portfolio"])
async def update_position(
    stock_code: str,
    position_request: UpdatePositionRequest,
    current_user: User = Depends(get_current_user)
):
    """Update portfolio position"""
    try:
        position = await signal_service.update_position(
            stock_code=stock_code,
            quantity=position_request.quantity,
            average_price=position_request.average_price,
            user_id=current_user.id
        )
        return PositionResponse.from_db(position)
    except Exception as e:
        logger.error(f"Failed to update position: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update position")


# ============================================================================
# SIGNALS ENDPOINTS
# ============================================================================

@app.get("/signals/daily", response_model=DailySignalsResponse, tags=["Signals"])
async def get_daily_signals(
    date: Optional[date] = None,
    current_user: User = Depends(get_current_user)
):
    """Get trading signals for a specific date"""
    try:
        target_date = date or datetime.now().date()
        signals = await signal_service.get_daily_signals(target_date)

        return DailySignalsResponse(
            date=target_date,
            signals=[TradingSignalResponse.from_db(s) for s in signals],
            generated_at=signals[0]['generated_at'] if signals else None,
            total_signals=len(signals)
        )
    except Exception as e:
        logger.error(f"Failed to get daily signals: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve signals")


@app.post("/signals/generate", response_model=SignalGenerationResponse, tags=["Signals"])
async def generate_signals(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """Manually trigger signal generation"""
    if not current_user.has_permission("generate_signals") and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        task_id = await signal_service.start_signal_generation()

        return SignalGenerationResponse(
            task_id=task_id,
            status=TaskStatus.STARTED,
            message="Signal generation started",
            started_at=datetime.now()
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to start signal generation: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to start signal generation")


@app.get("/signals/generation/{task_id}", response_model=SignalGenerationStatus, tags=["Signals"])
async def get_generation_status(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get signal generation task status"""
    try:
        status = await signal_service.get_generation_status(task_id)
        return SignalGenerationStatus(**status)
    except Exception as e:
        logger.error(f"Failed to get generation status: {str(e)}")
        raise HTTPException(status_code=404, detail="Task not found")


# ============================================================================
# ANALYTICS ENDPOINTS
# ============================================================================

@app.get("/analytics/performance", response_model=PerformanceAnalyticsResponse, tags=["Analytics"])
async def get_performance_analytics(
    days: int = 30,
    current_user: User = Depends(get_current_user)
):
    """Get performance analytics for specified period"""
    try:
        analytics = await signal_service.get_performance_analytics(days=days)
        return PerformanceAnalyticsResponse(**analytics)
    except Exception as e:
        logger.error(f"Failed to get performance analytics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve analytics")


@app.get("/analytics/stock/{stock_code}", tags=["Analytics"])
async def get_stock_analytics(
    stock_code: str,
    days: int = 30,
    db: Session = Depends(get_db_session)
):
    """Get analytics for a specific stock"""
    integration_service = DataIntegrationService(db)
    performance = integration_service.get_stock_historical_performance(stock_code, days=days)

    if not performance:
        raise HTTPException(status_code=404, detail="Stock not found or no data available")

    return performance


# ============================================================================
# RISK MANAGEMENT ENDPOINTS
# ============================================================================

@app.get("/risk/overview", response_model=RiskOverviewResponse, tags=["Risk Management"])
async def get_risk_overview(current_user: User = Depends(get_current_user)):
    """Get risk management overview"""
    try:
        overview = await risk_monitor.get_risk_overview()
        return RiskOverviewResponse(**overview)
    except Exception as e:
        logger.error(f"Failed to get risk overview: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve risk overview")


@app.get("/risk/alerts", response_model=List[RiskAlertResponse], tags=["Risk Management"])
async def get_risk_alerts(
    limit: int = 20,
    current_user: User = Depends(get_current_user)
):
    """Get recent risk alerts"""
    try:
        alerts = await risk_monitor.get_risk_alerts(limit=limit)
        return [RiskAlertResponse.from_db(alert) for alert in alerts]
    except Exception as e:
        logger.error(f"Failed to get risk alerts: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve risk alerts")


# ============================================================================
# ALERTS ENDPOINTS
# ============================================================================

@app.get("/alerts", response_model=List[AlertResponse], tags=["Alerts"])
async def get_alerts(
    limit: int = 100,
    offset: int = 0,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get alerts with filtering"""
    try:
        alerts = await alert_engine.get_alerts(
            limit=limit,
            offset=offset,
            status=status,
            priority=priority,
            user_id=current_user.id
        )
        return [AlertResponse.from_db(alert) for alert in alerts]
    except Exception as e:
        logger.error(f"Failed to get alerts: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve alerts")


@app.put("/alerts/{alert_id}/status", response_model=AlertResponse, tags=["Alerts"])
async def update_alert_status(
    alert_id: int,
    status_request: UpdateAlertStatusRequest,
    current_user: User = Depends(get_current_user)
):
    """Update alert status"""
    try:
        alert = await alert_engine.update_alert_status(
            alert_id=alert_id,
            status=status_request.status,
            notes=status_request.notes,
            user_id=current_user.id
        )
        return AlertResponse.from_db(alert)
    except Exception as e:
        logger.error(f"Failed to update alert: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update alert")


# ============================================================================
# DATA QUALITY ENDPOINTS
# ============================================================================

@app.get("/data/quality", tags=["Data Quality"])
async def get_data_quality(db: Session = Depends(get_db_session)):
    """Get data quality summary"""
    integration_service = DataIntegrationService(db)
    quality_summary = integration_service.get_data_quality_summary()
    return quality_summary


@app.get("/data/stocks", tags=["Data Quality"])
async def get_available_stocks(
    active_only: bool = True,
    db: Session = Depends(get_db_session)
):
    """Get list of available stocks"""
    try:
        query = db.query(StockMaster)

        if active_only:
            query = query.filter(StockMaster.is_active == True)

        stocks = query.order_by(StockMaster.stock_code).all()

        return {
            "stocks": [
                {
                    "stock_code": s.stock_code,
                    "company_name": s.company_name,
                    "sector": s.sector,
                    "industry": s.industry,
                    "is_lq45": s.is_lq45,
                    "market_cap_category": s.market_cap_category,
                    "last_price_update": s.last_price_update.isoformat() if s.last_price_update else None,
                    "data_quality_score": s.data_quality_score
                }
                for s in stocks
            ],
            "total": len(stocks)
        }
    except Exception as e:
        logger.error(f"Failed to get stocks: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve stocks")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
