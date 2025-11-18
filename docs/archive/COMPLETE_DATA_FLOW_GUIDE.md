# Complete Data Flow Guide - Project Aurum

## 🎯 Overview

This guide documents the complete end-to-end data flow from data collection through analysis to dashboard visualization.

---

## 📊 Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DATA COLLECTION LAYER                         │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
            ┌───────▼────────┐         ┌───────▼────────┐
            │  Yahoo Finance │         │   IDX Gateway  │
            │   (yfinance)   │         │   (Real-time)  │
            └───────┬────────┘         └───────┬────────┘
                    │                           │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │  Daily Price Scheduler    │
                    │  - Runs at 5:30 PM WIB    │
                    │  - Fetches OHLCV data     │
                    │  - Validates & cleans     │
                    └─────────────┬─────────────┘
                                  │
┌─────────────────────────────────▼─────────────────────────────────────┐
│                          DATABASE LAYER                                │
├────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐  ┌───────────────────┐  ┌─────────────────┐   │
│  │  stock_master    │  │ daily_stock_prices│  │ data_refresh_   │   │
│  │  - 40+ stocks    │  │ - Historical OHLCV│  │ logs            │   │
│  │  - Metadata      │  │ - Quality scores  │  │ - Audit trail   │   │
│  └──────────────────┘  └───────────────────┘  └─────────────────┘   │
│                                                                        │
│  ┌──────────────────┐  ┌───────────────────┐  ┌─────────────────┐   │
│  │ trading_signals  │  │ portfolio         │  │ alerts          │   │
│  │ - Daily signals  │  │ - Positions       │  │ - Notifications │   │
│  └──────────────────┘  └───────────────────┘  └─────────────────┘   │
└────────────────────────────────────────────────────────────────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │ Data Integration Service  │
                    │ - Transforms raw data     │
                    │ - Feature engineering     │
                    │ - Market analytics        │
                    └─────────────┬─────────────┘
                                  │
                         ┌────────┴────────┐
                         │                 │
              ┌──────────▼─────────┐  ┌───▼──────────────┐
              │  Signal Service    │  │  Analytics       │
              │  - ML inference    │  │  - Performance   │
              │  - Signal gen      │  │  - Sector stats  │
              │  - Risk scoring    │  │  - Market metrics│
              └──────────┬─────────┘  └───┬──────────────┘
                         │                 │
                         └────────┬────────┘
                                  │
┌─────────────────────────────────▼─────────────────────────────────────┐
│                            API LAYER                                   │
├────────────────────────────────────────────────────────────────────────┤
│  FastAPI REST Endpoints:                                               │
│  - /market/*        : Market data, indices, sectors                   │
│  - /signals/*       : Trading signals, generation                     │
│  - /portfolio/*     : Positions, summary, P&L                         │
│  - /analytics/*     : Performance metrics, insights                   │
│  - /alerts/*        : Notifications, risk alerts                      │
│  - /data/*          : Data quality, available stocks                  │
└────────────────────────────────────────────────────────────────────────┘
                                  │
                         ┌────────▼────────┐
                         │  WebSocket      │
                         │  Real-time      │
                         │  Updates        │
                         └────────┬────────┘
                                  │
┌─────────────────────────────────▼─────────────────────────────────────┐
│                       DASHBOARD / UI LAYER                             │
├────────────────────────────────────────────────────────────────────────┤
│  React Components:                                                     │
│  - MarketOverview    : Indices, market status, gainers/losers         │
│  - TradingSignals    : BUY/SELL/HOLD signals with confidence         │
│  - PortfolioOverview : Positions, P&L, sector allocation              │
│  - PerformanceChart  : Historical returns, risk metrics               │
│  - AlertsPanel       : Real-time notifications                        │
│  - RiskMonitor       : Portfolio risk, exposure limits                │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Complete Data Flow Steps

### Step 1: Data Collection (Automated Daily)

```python
# Runs at 5:30 PM Jakarta time every trading day
python -m src.data_pipeline.daily_price_scheduler

# Process:
1. Scheduler triggers at market close
2. DailyPriceFetcher fetches data from Yahoo Finance
3. Data validation (OHLC integrity, price anomalies)
4. Quality scoring (0-100 based on completeness)
5. Upsert to daily_stock_prices table (idempotent)
6. Update stock_master with quality scores
7. Log job execution to data_refresh_logs
```

**Data Stored:**
- `daily_stock_prices`: OHLCV + derived metrics (VWAP, price changes)
- `stock_master`: Stock metadata, last update timestamp
- `data_refresh_logs`: Audit trail with success/failure metrics

### Step 2: Data Integration & Feature Engineering

```python
# Data Integration Service bridges raw data → ML features
from src.data_pipeline.data_integration_service import DataIntegrationService

integration_service = DataIntegrationService(db_session)

# Get data ready for ML
feature_data = integration_service.prepare_feature_data_for_ml(
    stock_codes=['BBCA', 'BBRI', 'TLKM'],
    lookback_days=252
)

# Returns:
{
    'price_data': DataFrame,      # Ready for technical indicators
    'fundamental_data': DataFrame, # Financial metrics
    'metadata': DataFrame          # Sector, industry info
}
```

**Transformations:**
- Price data → Technical indicators (MA, RSI, MACD, Bollinger Bands)
- Volume patterns → Liquidity metrics
- Sector grouping → Relative strength analysis
- Quality flags → Filter unreliable data

### Step 3: Signal Generation

```python
# Signal Service orchestrates ML inference
from src.api.signal_service import SignalService

signal_service = SignalService(db_manager)
await signal_service.initialize()

# Trigger signal generation
task_id = await signal_service.start_signal_generation()

# Process:
1. Data collection via DataIntegrationService
2. Feature engineering (technical + fundamental + sentiment)
3. ML model inference (ensemble of XGBoost, RandomForest, etc.)
4. Signal generation with confidence scores
5. Risk adjustment based on portfolio constraints
6. Save to trading_signals table
7. Generate alerts for high-confidence signals
8. Cache results in Redis for fast dashboard access
```

**Output:**
- `trading_signals`: BUY/SELL/HOLD signals with scores
- `alerts`: High-priority signal notifications
- Redis cache: Latest signals for sub-second dashboard loading

### Step 4: Analytics & Aggregation

```python
# Analytics layer computes dashboard metrics
from src.data_pipeline.data_integration_service import DataIntegrationService

integration_service = DataIntegrationService(db_session)

# Market snapshot
snapshot = integration_service.get_market_snapshot()
# Returns: gainers, losers, volume, sector breakdown

# Performance metrics
performance = integration_service.get_stock_historical_performance(
    stock_code='BBCA',
    days=30
)
# Returns: returns, volatility, Sharpe ratio, max drawdown

# Sector analysis
sectors = integration_service.get_sector_performance(days=30)
# Returns: sector-wise returns, volatility, stock count
```

**Computed Metrics:**
- Market-wide: Advances/declines, volume, top movers
- Portfolio: Total P&L, sector allocation, risk scores
- Performance: Returns, Sharpe ratio, max drawdown, win rate
- Risk: VaR, position limits, concentration ratios

### Step 5: API Layer (FastAPI)

```python
# Complete API with all dashboard endpoints
# File: src/api/main_complete.py

# Market Data Endpoints
GET /market/status          # Open/closed, trading hours
GET /market/snapshot        # Gainers, losers, volume
GET /market/indices         # JCI, LQ45, IDX30
GET /market/sectors         # Sector performance

# Signal Endpoints
GET /signals/daily          # Today's trading signals
POST /signals/generate      # Trigger manual generation
GET /signals/generation/{id} # Check generation status

# Portfolio Endpoints
GET /portfolio/summary      # Aggregate metrics
GET /portfolio/positions    # All positions
PUT /portfolio/positions/{stock} # Update position

# Analytics Endpoints
GET /analytics/performance  # Historical metrics
GET /analytics/stock/{code} # Stock-specific analytics

# Risk Endpoints
GET /risk/overview          # Portfolio risk metrics
GET /risk/alerts            # Risk warnings

# Data Quality Endpoints
GET /data/quality           # Data refresh status
GET /data/stocks            # Available stocks
```

**Response Caching:**
- Redis TTL: 60s for real-time data
- 5min for analytics
- 15min for static data

### Step 6: Dashboard Visualization

```typescript
// Frontend data fetching (React + Zustand)
// File: apps/web_dashboard/frontend/src/store/dashboard.ts

import { apiClient } from '../lib/api-complete';

// Load all dashboard data in parallel
await Promise.all([
  apiClient.getMarketStatus(),
  apiClient.getDailySignals(),
  apiClient.getPortfolioSummary(),
  apiClient.getPositions(),
  apiClient.getRiskOverview(),
  apiClient.getPerformanceAnalytics(30)
]);

// Components auto-refresh every 30 seconds
// WebSocket pushes real-time signal updates
```

**Dashboard Components:**
- **MarketOverview**: Indices (JCI, LQ45), market status, top movers
- **TradingSignals**: Latest BUY/SELL signals with confidence
- **PortfolioOverview**: Positions, P&L, sector pie chart
- **PerformanceChart**: Equity curve, benchmark comparison
- **AlertsPanel**: Real-time notifications
- **RiskMonitor**: Risk metrics, exposure warnings

---

## 🔑 Key Integration Points

### 1. Price Data → Signal Generation

```python
# Bridge: DataIntegrationService provides clean data
feature_data = integration_service.prepare_feature_data_for_ml()

# Signal service consumes this
signals = signal_service._engineer_features(feature_data)
predictions = ml_model.predict(signals)
```

### 2. Signals → Dashboard

```python
# API endpoint serves cached signals
@app.get("/signals/daily")
async def get_daily_signals():
    # Check Redis cache first
    cached = await redis.get("latest_signals")
    if cached:
        return cached

    # Fallback to database
    return await signal_service.get_daily_signals(date.today())
```

### 3. Portfolio → Risk Management

```python
# Risk monitor tracks portfolio metrics
positions = await signal_service.get_current_positions()
risk_metrics = risk_monitor.calculate_portfolio_risk(positions)

# Generate alerts if limits breached
if risk_metrics['portfolio_volatility'] > threshold:
    await alert_engine.create_alert(
        type='RISK_WARNING',
        message='Portfolio volatility exceeds limit'
    )
```

---

## 📈 Data Quality & Monitoring

### Data Quality Checks

```python
# Automated validation at every stage

# 1. Collection Layer
- OHLC integrity (High >= Low, etc.)
- Price anomaly detection (>50% moves)
- Volume validation (non-negative)
- Missing data detection

# 2. Integration Layer
- Completeness scoring
- Consistency checks
- Timeliness monitoring
- Cross-source validation

# 3. Signal Layer
- Model confidence thresholds
- Prediction sanity checks
- Historical backtesting

# 4. API Layer
- Response time monitoring
- Error rate tracking
- Cache hit rates
```

### Monitoring Dashboard

```python
# Get data quality metrics
GET /data/quality

Response:
{
  "total_recent_jobs": 10,
  "successful_jobs": 9,
  "failed_jobs": 1,
  "avg_data_quality": 96.5,
  "total_records_processed": 2000,
  "latest_refresh": {
    "date": "2025-01-05",
    "status": "completed",
    "records": 200,
    "quality_score": 97.2
  }
}
```

---

## 🚀 Deployment Flow

### Development (Local)

```bash
# 1. Start database
# SQLite auto-created at data/trading_system.db

# 2. Setup stock data pipeline
python scripts/setup_stock_data_pipeline.py

# 3. Backfill historical data
python -m src.data_pipeline.daily_price_scheduler --backfill 2

# 4. Start API server
python src/api/main_complete.py

# 5. Start frontend
cd apps/web_dashboard/frontend
npm run dev
```

### Production

```bash
# 1. Database (PostgreSQL)
docker-compose up -d postgres

# 2. Setup pipeline
python scripts/setup_stock_data_pipeline.py

# 3. Start scheduler (as systemd service)
systemctl start stock-data-scheduler

# 4. Start API (with Gunicorn)
gunicorn src.api.main_complete:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000

# 5. Start frontend (nginx serves static build)
npm run build
# nginx serves from dist/
```

---

## 🔧 Troubleshooting

### Issue: Dashboard shows "No data"

**Check:**
1. Data pipeline ran successfully: `GET /data/quality`
2. Signals generated: `GET /signals/daily`
3. API accessible: `GET /health/detailed`
4. Frontend can reach API: Check CORS, network

**Fix:**
```bash
# Manually trigger data refresh
python -m src.data_pipeline.daily_price_scheduler --run-once

# Check logs
tail -f logs/data_pipeline.log
```

### Issue: Signals not updating

**Check:**
1. Signal service initialized: `GET /health/detailed`
2. ML model loaded: Check signal_service.model_loaded
3. Recent signal generation: `GET /signals/generation/{task_id}`

**Fix:**
```bash
# Manual signal generation via API
curl -X POST http://localhost:8000/signals/generate \
  -H "Authorization: Bearer $TOKEN"

# Or via Python
python scripts/manual_signal_generation.py
```

### Issue: Slow dashboard loading

**Check:**
1. Redis cache working: `redis-cli PING`
2. Database queries optimized: Check EXPLAIN ANALYZE
3. API response times: Monitor logs

**Fix:**
```bash
# Warm up Redis cache
curl http://localhost:8000/signals/daily
curl http://localhost:8000/portfolio/summary

# Rebuild indexes
python scripts/rebuild_database_indexes.py
```

---

## 📊 Performance Metrics

| Component | Target | Actual |
|-----------|--------|--------|
| Data fetch (daily) | <60s | ~30s |
| Signal generation | <5min | ~3min |
| API response (cached) | <100ms | ~50ms |
| API response (DB) | <500ms | ~200ms |
| Dashboard load | <2s | ~1.2s |
| WebSocket latency | <100ms | ~50ms |

---

## 🎯 Success Criteria

✅ **Data Pipeline**
- 99%+ data quality score
- Zero missed trading days
- <5min data availability after market close

✅ **Signal Generation**
- Signals generated within 5 minutes
- >95% model confidence on top signals
- <1% signal generation failures

✅ **API Performance**
- 99.9% uptime
- <500ms P95 response time
- <1% error rate

✅ **Dashboard UX**
- <2s initial load
- Real-time updates within 1s
- Responsive on mobile

---

## 📚 Related Documentation

- **Setup Guide**: `QUICKSTART_DATA_PIPELINE.md`
- **Data Pipeline**: `README_STOCK_DATA_PIPELINE.md`
- **API Reference**: `API_DOCUMENTATION.md` (auto-generated at `/docs`)
- **Cheat Sheet**: `DATA_PIPELINE_CHEATSHEET.md`

---

**Last Updated:** January 2025
**Version:** 2.0
