"""
Pydantic schemas for Indonesian Quantitative Trading Alert System
Request/Response models for API endpoints
"""

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, date, time
from enum import Enum


# Enums
class SignalType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    STRONG_BUY = "STRONG_BUY"
    STRONG_SELL = "STRONG_SELL"


class AlertPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    DISMISSED = "dismissed"
    EXPIRED = "expired"
    RESOLVED = "resolved"


class TaskStatus(str, Enum):
    PENDING = "pending"
    STARTED = "started"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class UserRole(str, Enum):
    ADMIN = "admin"
    TRADER = "trader"
    VIEWER = "viewer"
    API_USER = "api_user"


# Authentication Schemas
class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=12)


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int
    user: Optional[Dict[str, Any]] = None


class UserProfile(BaseModel):
    id: str
    username: str
    email: str
    role: UserRole
    permissions: Dict[str, bool]
    created_at: datetime
    last_login: Optional[datetime] = None


class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., pattern=r'^[^@]+@[^@]+\.[^@]+$')
    password: str = Field(..., min_length=8)
    role: UserRole = UserRole.TRADER
    permissions: Optional[Dict[str, bool]] = None


# Alert Schemas
class CreateAlertRequest(BaseModel):
    alert_type: str = Field(..., min_length=1, max_length=50)
    message: str = Field(..., min_length=1, max_length=1000)
    priority: AlertPriority = AlertPriority.MEDIUM
    stock_code: Optional[str] = Field(None, max_length=10)
    metadata: Optional[Dict[str, Any]] = None
    expires_at: Optional[datetime] = None


class UpdateAlertStatusRequest(BaseModel):
    status: AlertStatus
    notes: Optional[str] = Field(None, max_length=500)


class AlertResponse(BaseModel):
    id: int
    alert_type: str
    message: str
    priority: AlertPriority
    status: AlertStatus
    stock_code: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    expires_at: Optional[datetime] = None

    @classmethod
    def from_db(cls, db_record: Dict[str, Any]) -> "AlertResponse":
        """Create AlertResponse from database record"""
        return cls(
            id=db_record['id'],
            alert_type=db_record['alert_type'],
            message=db_record['message'],
            priority=AlertPriority(db_record['priority']),
            status=AlertStatus(db_record['status']),
            stock_code=db_record.get('stock_code'),
            metadata=db_record.get('meta_data', {}),
            created_at=db_record['created_at'],
            updated_at=db_record['updated_at'],
            acknowledged_at=db_record.get('acknowledged_at'),
            acknowledged_by=str(db_record['acknowledged_by']) if db_record.get('acknowledged_by') else None,
            expires_at=db_record.get('expires_at')
        )


# Signal Schemas
class TradingSignalResponse(BaseModel):
    id: int
    date: datetime
    stock_code: str
    sector: Optional[str] = None
    signal_type: SignalType
    composite_score: float = Field(..., ge=-1, le=1)
    confidence: float = Field(..., ge=0, le=1)
    position_size: float = Field(..., ge=0, le=1)
    current_price: float = Field(..., gt=0)
    volume: Optional[float] = None
    technical_score: Optional[float] = None
    fundamental_score: Optional[float] = None
    sentiment_score: Optional[float] = None
    risk_adjusted: bool = False
    metadata: Optional[Dict[str, Any]] = None
    generated_at: datetime

    @classmethod
    def from_db(cls, db_record: Dict[str, Any]) -> "TradingSignalResponse":
        """Create TradingSignalResponse from database record"""
        return cls(
            id=db_record['id'],
            date=db_record['date'],
            stock_code=db_record['stock_code'],
            sector=db_record.get('sector'),
            signal_type=SignalType(db_record['signal_type']),
            composite_score=float(db_record['composite_score']),
            confidence=float(db_record['confidence']),
            position_size=float(db_record['position_size']),
            current_price=float(db_record['current_price']),
            volume=float(db_record['volume']) if db_record.get('volume') else None,
            technical_score=float(db_record['technical_score']) if db_record.get('technical_score') else None,
            fundamental_score=float(db_record['fundamental_score']) if db_record.get('fundamental_score') else None,
            sentiment_score=float(db_record['sentiment_score']) if db_record.get('sentiment_score') else None,
            risk_adjusted=bool(db_record.get('risk_adjusted', False)),
            metadata=db_record.get('meta_data', {}),
            generated_at=db_record['generated_at']
        )


class DailySignalsResponse(BaseModel):
    date: date
    signals: List[TradingSignalResponse]
    generated_at: Optional[datetime] = None
    total_signals: int


class SignalGenerationResponse(BaseModel):
    task_id: str
    status: TaskStatus
    message: str
    started_at: datetime


class SignalGenerationStatus(BaseModel):
    task_id: str
    status: TaskStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    signals_generated: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


# Portfolio Schemas
class PositionResponse(BaseModel):
    id: int
    stock_code: str
    quantity: int
    average_price: float = Field(..., gt=0)
    current_price: Optional[float] = None
    sector: Optional[str] = None
    market_value: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    unrealized_pnl_percent: Optional[float] = None
    position_size_percent: Optional[float] = None
    last_updated: datetime

    @classmethod
    def from_db(cls, db_record: Dict[str, Any]) -> "PositionResponse":
        """Create PositionResponse from database record"""
        return cls(
            id=db_record['id'],
            stock_code=db_record['stock_code'],
            quantity=int(db_record['quantity']),
            average_price=float(db_record['average_price']),
            current_price=float(db_record['current_price']) if db_record.get('current_price') else None,
            sector=db_record.get('sector'),
            market_value=float(db_record['market_value']) if db_record.get('market_value') else None,
            unrealized_pnl=float(db_record['unrealized_pnl']) if db_record.get('unrealized_pnl') else None,
            unrealized_pnl_percent=float(db_record['unrealized_pnl_percent']) if db_record.get('unrealized_pnl_percent') else None,
            position_size_percent=float(db_record['position_size_percent']) if db_record.get('position_size_percent') else None,
            last_updated=db_record['last_updated']
        )


class UpdatePositionRequest(BaseModel):
    stock_code: str = Field(..., min_length=1, max_length=10)
    quantity: int = Field(..., ge=0)
    average_price: float = Field(..., gt=0)


class PortfolioSummaryResponse(BaseModel):
    total_positions: int
    total_market_value: float
    total_cost_basis: float
    total_unrealized_pnl: float
    total_unrealized_pnl_percent: float
    sector_breakdown: Dict[str, float]
    cash_available: Optional[float] = None
    portfolio_beta: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    last_updated: datetime


# Risk Management Schemas
class RiskMetric(BaseModel):
    name: str
    current_value: float
    limit_value: float
    warning_threshold: float
    critical_threshold: float
    status: str  # "normal", "warning", "critical"
    description: str


class RiskOverviewResponse(BaseModel):
    risk_metrics: Dict[str, RiskMetric]
    alert_counts: Dict[str, int]
    monitoring_status: str
    last_check: Optional[datetime] = None
    portfolio_risk_score: Optional[float] = None


class RiskAlertResponse(BaseModel):
    id: str
    alert_type: str
    severity: str
    message: str
    stock_code: Optional[str] = None
    sector: Optional[str] = None
    current_value: float
    limit_value: float
    timestamp: datetime

    @classmethod
    def from_db(cls, db_record: Dict[str, Any]) -> "RiskAlertResponse":
        """Create RiskAlertResponse from database record"""
        return cls(
            id=str(db_record['id']),
            alert_type=db_record['alert_type'],
            severity=db_record['severity'],
            message=db_record['message'],
            stock_code=db_record.get('stock_code'),
            sector=db_record.get('sector'),
            current_value=float(db_record['current_value']),
            limit_value=float(db_record['threshold_value']),
            timestamp=db_record['created_at']
        )


class UpdateRiskLimitsRequest(BaseModel):
    limits: Dict[str, Dict[str, float]]

    @validator('limits')
    def validate_limits(cls, v):
        required_fields = ['limit_value', 'warning_threshold', 'critical_threshold']
        for metric_type, config in v.items():
            for field in required_fields:
                if field not in config:
                    raise ValueError(f"Missing required field '{field}' for metric '{metric_type}'")
                if not isinstance(config[field], (int, float)) or config[field] < 0:
                    raise ValueError(f"Invalid value for '{field}' in metric '{metric_type}'")
        return v


# Market Data Schemas
class MarketStatusResponse(BaseModel):
    is_open: bool
    current_time: datetime
    next_open: Optional[datetime] = None
    next_close: Optional[datetime] = None
    session_type: str  # "regular", "pre_market", "after_hours", "closed"


class StockPriceResponse(BaseModel):
    stock_code: str
    current_price: float
    change: Optional[float] = None
    change_percent: Optional[float] = None
    volume: Optional[float] = None
    timestamp: datetime


# Analytics Schemas
class PerformanceMetrics(BaseModel):
    period_days: int
    total_return: Optional[float] = None
    annualized_return: Optional[float] = None
    volatility: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    win_rate: Optional[float] = None
    avg_trade_return: Optional[float] = None


class PerformanceAnalyticsResponse(BaseModel):
    period_days: int
    total_signals: int
    signal_type_distribution: Dict[str, int]
    avg_confidence: float
    avg_position_size: float
    avg_daily_signals: float
    daily_signal_counts: Dict[str, int]
    performance_metrics: Optional[PerformanceMetrics] = None
    analysis_date: datetime


# Report Schemas
class DailyReportRequest(BaseModel):
    date: Optional[date] = None
    format: str = Field("json", pattern="^(json|pdf|csv)$")
    include_charts: bool = True
    email_recipients: Optional[List[str]] = None


class ReportResponse(BaseModel):
    report_id: str
    date: date
    format: str
    status: str  # "generated", "processing", "failed"
    download_url: Optional[str] = None
    generated_at: datetime
    file_size: Optional[int] = None


# WebSocket Schemas
class WebSocketMessage(BaseModel):
    type: str
    data: Dict[str, Any]
    timestamp: datetime


class AlertUpdate(WebSocketMessage):
    type: str = "alert_update"


class SignalUpdate(WebSocketMessage):
    type: str = "signal_update"


class RiskUpdate(WebSocketMessage):
    type: str = "risk_update"


class PortfolioUpdate(WebSocketMessage):
    type: str = "portfolio_update"


# System Schemas
class HealthCheckResponse(BaseModel):
    status: str
    timestamp: datetime
    service: str
    version: str
    services: Optional[Dict[str, str]] = None


class SystemMetrics(BaseModel):
    uptime_seconds: float
    memory_usage_mb: float
    cpu_usage_percent: float
    active_connections: int
    total_requests: int
    average_response_time_ms: float


class SystemStatusResponse(BaseModel):
    status: str
    timestamp: datetime
    services: Dict[str, str]
    metrics: SystemMetrics
    last_signal_generation: Optional[datetime] = None
    active_alerts: int
    portfolio_positions: int


class AIResearchReportResponse(BaseModel):
    stock_code: str
    trade_date: date
    analyst_notes: Dict[str, str]
    debate_summary: str
    risk_assessment: str
    final_recommendation: str
    conviction: float
    timestamp: datetime


class AuctionMarketProfileResponse(BaseModel):
    stock_code: str
    session_date: date
    point_of_control: float
    value_area_high: float
    value_area_low: float
    initial_balance_high: Optional[float] = None
    initial_balance_low: Optional[float] = None
    profile_type: Optional[str] = None
    total_volume: Optional[float] = None
    vwap: Optional[float] = None
    session_range: Optional[float] = None
    open_price: Optional[float] = None
    close_price: Optional[float] = None
    single_prints: Optional[List[float]] = None
    metrics: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


# Configuration Schemas
class NotificationConfig(BaseModel):
    email_enabled: bool
    telegram_enabled: bool
    sms_enabled: bool
    webhook_enabled: bool
    default_priority_threshold: AlertPriority


class RiskConfig(BaseModel):
    max_position_size: float = Field(..., gt=0, le=1)
    max_sector_concentration: float = Field(..., gt=0, le=1)
    max_portfolio_volatility: float = Field(..., gt=0, le=1)
    max_drawdown: float = Field(..., gt=0, le=1)
    risk_check_interval_minutes: int = Field(..., gt=0, le=60)


class UpdateConfigRequest(BaseModel):
    notification_config: Optional[NotificationConfig] = None
    risk_config: Optional[RiskConfig] = None
    signal_config: Optional[Dict[str, Any]] = None


# Error Schemas
class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    timestamp: datetime
    request_id: Optional[str] = None


class ValidationErrorResponse(BaseModel):
    error: str = "Validation Error"
    detail: List[Dict[str, Any]]
    timestamp: datetime


# Pagination Schemas
class PaginationParams(BaseModel):
    limit: int = Field(100, ge=1, le=1000)
    offset: int = Field(0, ge=0)


class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    limit: int
    offset: int
    has_next: bool
    has_previous: bool


# Filter Schemas
class DateRangeFilter(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    @validator('end_date')
    def end_date_after_start_date(cls, v, values):
        if v and values.get('start_date') and v < values['start_date']:
            raise ValueError('end_date must be after start_date')
        return v


class SignalFilter(DateRangeFilter):
    signal_types: Optional[List[SignalType]] = None
    stock_codes: Optional[List[str]] = None
    sectors: Optional[List[str]] = None
    min_confidence: Optional[float] = Field(None, ge=0, le=1)
    max_confidence: Optional[float] = Field(None, ge=0, le=1)

    @validator('max_confidence')
    def max_confidence_greater_than_min(cls, v, values):
        if v and values.get('min_confidence') and v < values['min_confidence']:
            raise ValueError('max_confidence must be greater than min_confidence')
        return v


class AlertFilter(DateRangeFilter):
    priorities: Optional[List[AlertPriority]] = None
    statuses: Optional[List[AlertStatus]] = None
    alert_types: Optional[List[str]] = None
    stock_codes: Optional[List[str]] = None
