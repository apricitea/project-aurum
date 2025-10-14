"""
Database Extensions for Daily Stock Price Data
Enhanced tables for historical daily prices, stock metadata, and ETL tracking
"""

from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, Date, Index, UniqueConstraint, Text
from sqlalchemy.types import JSON
from datetime import datetime
import uuid

from .database import Base, GUID, JSONB


class StockMaster(Base):
    """
    Master table for stock metadata
    Single source of truth for stock information
    """
    __tablename__ = "stock_master"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(10), unique=True, nullable=False, index=True)  # e.g., BBCA, BBRI
    yahoo_symbol = Column(String(20), unique=True, nullable=False)  # e.g., BBCA.JK, BBRI.JK
    company_name = Column(String(200), nullable=False)
    sector = Column(String(100), index=True)
    industry = Column(String(100))
    exchange = Column(String(20), default="IDX")
    currency = Column(String(10), default="IDR")

    # Listing information
    listing_date = Column(Date)
    delisting_date = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True, index=True)

    # Market classification
    market_cap_category = Column(String(20))  # Large, Mid, Small
    is_lq45 = Column(Boolean, default=False, index=True)  # Is in LQ45 index
    is_idx30 = Column(Boolean, default=False)

    # Metadata
    description = Column(Text)
    website = Column(String(200))
    isin_code = Column(String(20))

    # Data quality tracking
    last_price_update = Column(DateTime)
    data_quality_score = Column(Float)  # 0-100 score based on data completeness

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Additional metadata
    meta_data = Column(JSONB, default={})

    __table_args__ = (
        Index('idx_stock_master_active_sector', 'is_active', 'sector'),
        Index('idx_stock_master_lq45_active', 'is_lq45', 'is_active'),
    )


class DailyStockPrice(Base):
    """
    Historical daily OHLCV data for stocks
    Optimized for analytics and backtesting
    Design principles:
    - Partitioned by date for query performance
    - Indexed for common query patterns
    - Validated data quality
    - Supports data correction/restatement
    """
    __tablename__ = "daily_stock_prices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(10), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)

    # OHLCV data
    open_price = Column(Float, nullable=False)
    high_price = Column(Float, nullable=False)
    low_price = Column(Float, nullable=False)
    close_price = Column(Float, nullable=False)
    adjusted_close = Column(Float)  # Adjusted for splits/dividends
    volume = Column(Float, nullable=False)

    # Derived metrics
    vwap = Column(Float)  # Volume-weighted average price
    trade_count = Column(Integer)
    turnover_value = Column(Float)  # Total value traded

    # Market context
    market_cap = Column(Float)
    shares_outstanding = Column(Float)

    # Price changes
    price_change = Column(Float)  # Absolute change from previous close
    price_change_percent = Column(Float)  # Percentage change

    # Data quality indicators
    is_trading_day = Column(Boolean, default=True)
    is_corporate_action = Column(Boolean, default=False)  # Stock split, dividend, etc.
    data_source = Column(String(50), default="yfinance")  # Data source identifier
    data_quality = Column(String(20), default="verified")  # verified, estimated, corrected

    # Timestamps and versioning
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Additional metadata (corporate actions, anomalies, etc.)
    meta_data = Column(JSONB, default={})

    __table_args__ = (
        # Unique constraint: one record per stock per date
        UniqueConstraint('stock_code', 'date', name='uq_stock_date'),

        # Composite indexes for common query patterns
        Index('idx_daily_prices_stock_date_desc', 'stock_code', 'date', postgresql_ops={'date': 'DESC'}),
        Index('idx_daily_prices_date_stock', 'date', 'stock_code'),
        Index('idx_daily_prices_date_volume', 'date', 'volume', postgresql_ops={'volume': 'DESC'}),

        # Index for data quality queries
        Index('idx_daily_prices_quality', 'data_quality', 'date'),
    )


class DataRefreshLog(Base):
    """
    Audit log for data refresh jobs
    Tracks ETL job execution, success/failure, and data quality
    """
    __tablename__ = "data_refresh_logs"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    job_name = Column(String(100), nullable=False, index=True)
    job_type = Column(String(50), nullable=False)  # daily_prices, fundamentals, realtime

    # Execution details
    started_at = Column(DateTime, nullable=False, index=True)
    completed_at = Column(DateTime)
    duration_seconds = Column(Float)
    status = Column(String(20), nullable=False, index=True)  # running, completed, failed, partial

    # Data scope
    target_date = Column(Date, index=True)  # Date being refreshed
    stock_codes = Column(JSONB)  # List of stock codes processed

    # Results
    records_processed = Column(Integer, default=0)
    records_inserted = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)

    # Error tracking
    error_message = Column(Text)
    error_details = Column(JSONB)
    retry_count = Column(Integer, default=0)

    # Data quality metrics
    data_quality_score = Column(Float)  # Overall quality score for this refresh
    validation_errors = Column(JSONB)  # List of validation errors

    # Resource usage
    memory_used_mb = Column(Float)
    api_calls_made = Column(Integer)
    api_quota_remaining = Column(Integer)

    # Metadata
    meta_data = Column(JSONB, default={})

    __table_args__ = (
        Index('idx_refresh_log_job_date', 'job_name', 'target_date', 'status'),
        Index('idx_refresh_log_status_started', 'status', 'started_at', postgresql_ops={'started_at': 'DESC'}),
    )


class StockFundamentals(Base):
    """
    Fundamental data for stocks (quarterly/annual)
    Financial metrics for analysis and screening
    """
    __tablename__ = "stock_fundamentals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(10), nullable=False, index=True)
    report_date = Column(Date, nullable=False, index=True)  # Reporting period end date
    report_type = Column(String(20), nullable=False)  # quarterly, annual

    # Valuation metrics
    market_cap = Column(Float)
    pe_ratio = Column(Float)
    pb_ratio = Column(Float)
    ps_ratio = Column(Float)
    dividend_yield = Column(Float)

    # Profitability
    revenue = Column(Float)
    net_income = Column(Float)
    ebitda = Column(Float)
    gross_profit = Column(Float)
    operating_income = Column(Float)

    # Margins
    gross_margin = Column(Float)
    operating_margin = Column(Float)
    profit_margin = Column(Float)

    # Balance sheet
    total_assets = Column(Float)
    total_liabilities = Column(Float)
    total_equity = Column(Float)
    cash_and_equivalents = Column(Float)
    total_debt = Column(Float)

    # Ratios
    current_ratio = Column(Float)
    debt_to_equity = Column(Float)
    return_on_equity = Column(Float)
    return_on_assets = Column(Float)

    # Per share metrics
    earnings_per_share = Column(Float)
    book_value_per_share = Column(Float)

    # Data metadata
    data_source = Column(String(50), default="yfinance")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    meta_data = Column(JSONB, default={})

    __table_args__ = (
        UniqueConstraint('stock_code', 'report_date', 'report_type', name='uq_stock_fundamentals'),
        Index('idx_fundamentals_stock_date', 'stock_code', 'report_date', postgresql_ops={'report_date': 'DESC'}),
    )


class DataQualityMetric(Base):
    """
    Data quality metrics and monitoring
    Tracks data completeness, accuracy, timeliness
    """
    __tablename__ = "data_quality_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    metric_date = Column(Date, nullable=False, index=True)
    metric_name = Column(String(100), nullable=False, index=True)
    metric_category = Column(String(50))  # completeness, accuracy, timeliness, consistency

    # Metric values
    metric_value = Column(Float, nullable=False)
    threshold_value = Column(Float)
    is_passing = Column(Boolean, default=True, index=True)

    # Scope
    stock_code = Column(String(10), index=True)  # NULL for market-wide metrics
    data_source = Column(String(50))

    # Details
    description = Column(Text)
    impact_level = Column(String(20))  # low, medium, high, critical

    # Timestamps
    measured_at = Column(DateTime, default=datetime.utcnow, index=True)
    meta_data = Column(JSONB, default={})

    __table_args__ = (
        Index('idx_quality_date_category', 'metric_date', 'metric_category', 'is_passing'),
    )
