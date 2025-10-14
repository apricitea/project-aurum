# Integration Checklist - Complete Data Flow

## ✅ Pre-Deployment Checklist

Use this checklist to ensure all components are properly connected and working.

---

## 📋 Phase 1: Database Setup

- [ ] **Install dependencies**
  ```bash
  pip install yfinance pandas sqlalchemy schedule pytz
  ```

- [ ] **Run database setup**
  ```bash
  python scripts/setup_stock_data_pipeline.py
  ```
  Expected: "✓ Stock Master: 40 total, 40 active, 25 LQ45"

- [ ] **Verify tables created**
  ```sql
  -- Check PostgreSQL/SQLite
  SELECT table_name FROM information_schema.tables
  WHERE table_schema = 'public';

  -- Should see:
  -- stock_master, daily_stock_prices, data_refresh_logs,
  -- stock_fundamentals, data_quality_metrics,
  -- trading_signals, portfolio, alerts, etc.
  ```

- [ ] **Check indexes**
  ```sql
  SELECT indexname FROM pg_indexes
  WHERE tablename = 'daily_stock_prices';

  -- Should see:
  -- idx_daily_prices_stock_date_desc
  -- idx_daily_prices_date_stock
  -- idx_daily_prices_date_volume
  ```

---

## 📋 Phase 2: Data Pipeline

- [ ] **Backfill historical data (2 years)**
  ```bash
  python -m src.data_pipeline.daily_price_scheduler --backfill 2
  ```
  Expected: "Job completed: 20,160 inserted" (40 stocks × 504 days)

- [ ] **Verify data loaded**
  ```sql
  SELECT stock_code, COUNT(*) as days, MAX(date) as latest_date
  FROM daily_stock_prices
  GROUP BY stock_code
  ORDER BY stock_code;

  -- Should see ~500 days per stock
  ```

- [ ] **Check data quality**
  ```bash
  curl http://localhost:8000/data/quality
  ```
  Expected: avg_data_quality > 95

- [ ] **Test manual refresh**
  ```bash
  python -m src.data_pipeline.daily_price_scheduler --run-once
  ```
  Expected: "✓ BBCA: X records saved, quality: 98.5%"

- [ ] **Start automated scheduler**
  ```bash
  python -m src.data_pipeline.daily_price_scheduler
  ```
  Expected: "Next run: 2025-XX-XX 17:30:00"

---

## 📋 Phase 3: Data Integration

- [ ] **Test DataIntegrationService**
  ```python
  from sqlalchemy import create_engine
  from sqlalchemy.orm import sessionmaker
  from src.data_pipeline.data_integration_service import DataIntegrationService

  engine = create_engine("sqlite:///data/trading_system.db")
  Session = sessionmaker(bind=engine)
  session = Session()

  service = DataIntegrationService(session)

  # Test price data retrieval
  df = service.get_latest_prices_dataframe(days=30)
  assert len(df) > 0, "No price data found"
  print(f"✓ Retrieved {len(df)} price records")

  # Test market snapshot
  snapshot = service.get_market_snapshot()
  assert 'total_stocks' in snapshot, "Snapshot missing fields"
  print(f"✓ Market snapshot: {snapshot['total_stocks']} stocks")

  # Test ML feature data
  feature_data = service.prepare_feature_data_for_ml()
  assert not feature_data['price_data'].empty, "No feature data"
  print(f"✓ Feature data ready: {len(feature_data['price_data'])} rows")
  ```

- [ ] **Verify data transformations**
  - Price data has all required columns (open, high, low, close, volume)
  - Metadata merged correctly (sector, industry)
  - Derived metrics calculated (VWAP, price changes)

---

## 📋 Phase 4: API Layer

- [ ] **Start API server**
  ```bash
  # Development
  python src/api/main_complete.py

  # Production
  gunicorn src.api.main_complete:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000
  ```

- [ ] **Test health endpoints**
  ```bash
  curl http://localhost:8000/health
  # Expected: {"status": "healthy"}

  curl http://localhost:8000/health/detailed
  # Expected: All services "healthy"
  ```

- [ ] **Test market data endpoints**
  ```bash
  # Market status
  curl http://localhost:8000/market/status
  # Expected: {"is_open": true/false, "session_type": "..."}

  # Market snapshot
  curl http://localhost:8000/market/snapshot
  # Expected: {"total_stocks": 40, "advancers": X, ...}

  # Market indices
  curl http://localhost:8000/market/indices
  # Expected: {"indices": [{"code": "JCI", ...}, {"code": "LQ45", ...}]}

  # Sector performance
  curl http://localhost:8000/market/sectors?days=30
  # Expected: {"sectors": [...]}
  ```

- [ ] **Test signal endpoints**
  ```bash
  # Daily signals (requires auth)
  curl -H "Authorization: Bearer $TOKEN" \
    http://localhost:8000/signals/daily
  # Expected: {"date": "...", "signals": [...], "total_signals": X}
  ```

- [ ] **Test portfolio endpoints**
  ```bash
  # Portfolio summary
  curl -H "Authorization: Bearer $TOKEN" \
    http://localhost:8000/portfolio/summary
  # Expected: {"total_positions": X, "total_market_value": Y, ...}

  # Positions
  curl -H "Authorization: Bearer $TOKEN" \
    http://localhost:8000/portfolio/positions
  # Expected: [{stock_code: "...", quantity: X, ...}, ...]
  ```

- [ ] **Test analytics endpoints**
  ```bash
  # Performance analytics
  curl -H "Authorization: Bearer $TOKEN" \
    http://localhost:8000/analytics/performance?days=30
  # Expected: {"period_days": 30, "total_signals": X, ...}

  # Stock analytics
  curl http://localhost:8000/analytics/stock/BBCA?days=30
  # Expected: {"stock_code": "BBCA", "total_return": X, ...}
  ```

- [ ] **Test data quality endpoints**
  ```bash
  # Data quality
  curl http://localhost:8000/data/quality
  # Expected: {"avg_data_quality": X, "successful_jobs": Y, ...}

  # Available stocks
  curl http://localhost:8000/data/stocks
  # Expected: {"stocks": [...], "total": 40}
  ```

- [ ] **Test authentication**
  ```bash
  # Login
  curl -X POST http://localhost:8000/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username": "admin", "password": "admin123"}'
  # Expected: {"access_token": "...", "token_type": "bearer"}

  # Get current user
  curl -H "Authorization: Bearer $TOKEN" \
    http://localhost:8000/auth/me
  # Expected: {"username": "admin", "role": "admin", ...}
  ```

---

## 📋 Phase 5: Frontend Integration

- [ ] **Install dependencies**
  ```bash
  cd apps/web_dashboard/frontend
  npm install
  ```

- [ ] **Configure API endpoint**
  ```bash
  # Create .env file
  echo "VITE_API_URL=http://localhost:8000" > .env
  ```

- [ ] **Update API client**
  ```bash
  # Replace src/lib/api.ts with src/lib/api-complete.ts
  mv src/lib/api-complete.ts src/lib/api.ts
  ```

- [ ] **Test API client**
  ```typescript
  import { apiClient } from './lib/api';

  // Test market data
  const snapshot = await apiClient.getMarketSnapshot();
  console.log('Market snapshot:', snapshot);

  // Test authentication
  const token = await apiClient.login({
    username: 'admin',
    password: 'admin123'
  });
  console.log('Logged in:', token);

  // Test signals
  const signals = await apiClient.getDailySignals();
  console.log('Signals:', signals);
  ```

- [ ] **Start frontend**
  ```bash
  npm run dev
  ```
  Expected: "Local: http://localhost:5173"

- [ ] **Verify dashboard components load**
  - [ ] Market Overview shows JCI, LQ45 indices
  - [ ] Trading Signals shows BUY/SELL recommendations
  - [ ] Portfolio Overview shows positions and P&L
  - [ ] Performance Chart renders
  - [ ] Alerts Panel shows notifications
  - [ ] Risk Monitor displays metrics

---

## 📋 Phase 6: End-to-End Testing

- [ ] **Test complete data flow**
  1. **Trigger data refresh**
     ```bash
     python -m src.data_pipeline.daily_price_scheduler --run-once
     ```

  2. **Verify data in database**
     ```sql
     SELECT * FROM daily_stock_prices
     WHERE date = CURRENT_DATE
     ORDER BY stock_code;
     ```

  3. **Generate signals**
     ```bash
     curl -X POST http://localhost:8000/signals/generate \
       -H "Authorization: Bearer $TOKEN"
     ```

  4. **Check dashboard updates**
     - Open browser to http://localhost:5173
     - Verify new signals appear
     - Check updated prices in portfolio
     - Confirm alerts triggered

- [ ] **Test real-time updates**
  - [ ] Dashboard auto-refreshes every 30s
  - [ ] WebSocket receives updates (if implemented)
  - [ ] New alerts appear without refresh

- [ ] **Test error handling**
  - [ ] API returns proper error messages
  - [ ] Frontend shows error states gracefully
  - [ ] Failed data fetches retry automatically

---

## 📋 Phase 7: Performance Validation

- [ ] **API Response Times**
  ```bash
  # Test with Apache Bench
  ab -n 100 -c 10 http://localhost:8000/market/snapshot

  # Expected:
  # - Mean: <200ms
  # - P95: <500ms
  # - P99: <1000ms
  ```

- [ ] **Database Query Performance**
  ```sql
  -- Test key queries
  EXPLAIN ANALYZE
  SELECT * FROM daily_stock_prices
  WHERE stock_code = 'BBCA'
    AND date >= CURRENT_DATE - INTERVAL '30 days'
  ORDER BY date DESC;

  -- Expected: Index Scan, <10ms execution
  ```

- [ ] **Frontend Load Time**
  - Initial load: <2s
  - API calls complete: <500ms each
  - Charts render: <1s

- [ ] **Data Pipeline Performance**
  - Daily refresh (40 stocks): <60s
  - Signal generation: <5min
  - Analytics computation: <30s

---

## 📋 Phase 8: Data Quality Validation

- [ ] **Verify data completeness**
  ```sql
  -- Check for missing dates
  SELECT stock_code,
         COUNT(*) as total_days,
         MAX(date) as latest_date
  FROM daily_stock_prices
  WHERE date >= CURRENT_DATE - INTERVAL '30 days'
  GROUP BY stock_code
  HAVING COUNT(*) < 20;  -- Flag stocks with <20 trading days

  -- Should return no rows
  ```

- [ ] **Check data quality scores**
  ```sql
  SELECT stock_code, data_quality_score
  FROM stock_master
  WHERE data_quality_score < 90
  ORDER BY data_quality_score;

  -- Investigate any stocks with quality < 90
  ```

- [ ] **Validate OHLC integrity**
  ```sql
  -- Find invalid OHLC relationships
  SELECT stock_code, date, open_price, high_price, low_price, close_price
  FROM daily_stock_prices
  WHERE high_price < low_price
     OR high_price < open_price
     OR high_price < close_price
     OR low_price > open_price
     OR low_price > close_price;

  -- Should return no rows
  ```

---

## 📋 Phase 9: Security & Access Control

- [ ] **Test authentication flow**
  - [ ] Admin can generate signals
  - [ ] Trader can view signals but not generate
  - [ ] Viewer has read-only access
  - [ ] Unauthenticated users blocked

- [ ] **Verify JWT tokens**
  - [ ] Tokens expire correctly
  - [ ] Refresh token flow works
  - [ ] Invalid tokens rejected

- [ ] **Check CORS settings**
  - [ ] Frontend origin allowed
  - [ ] Other origins blocked
  - [ ] Credentials included correctly

---

## 📋 Phase 10: Monitoring & Logging

- [ ] **Setup logging**
  ```python
  # Logs should include:
  # - Data refresh status
  # - Signal generation progress
  # - API request/response times
  # - Errors with stack traces
  ```

- [ ] **Monitor key metrics**
  - [ ] Daily data refresh success rate: >99%
  - [ ] Signal generation success rate: >95%
  - [ ] API uptime: >99.9%
  - [ ] Average response time: <200ms

- [ ] **Setup alerts**
  - [ ] Data refresh failures
  - [ ] Signal generation errors
  - [ ] API error rate >1%
  - [ ] Database connection issues

---

## 🎯 Final Validation

### All Systems Green Checklist

- [ ] ✅ Database has 40+ stocks with 2+ years of data
- [ ] ✅ Data quality score >95% average
- [ ] ✅ Daily scheduler running and logged next run time
- [ ] ✅ API health check returns all services "healthy"
- [ ] ✅ All market endpoints returning data
- [ ] ✅ Signals being generated successfully
- [ ] ✅ Portfolio tracking working
- [ ] ✅ Dashboard loading in <2s
- [ ] ✅ All components rendering correctly
- [ ] ✅ Real-time updates working
- [ ] ✅ Authentication and authorization working
- [ ] ✅ Logging and monitoring in place

### Performance Benchmarks Met

- [ ] ✅ Data fetch: <60s (40 stocks)
- [ ] ✅ Signal generation: <5min
- [ ] ✅ API response (cached): <100ms
- [ ] ✅ API response (DB): <500ms
- [ ] ✅ Dashboard load: <2s
- [ ] ✅ Database queries: <50ms (indexed)

### Data Quality Standards Met

- [ ] ✅ No missing trading days in last 30 days
- [ ] ✅ All OHLC data valid (high >= low, etc.)
- [ ] ✅ Stock metadata complete
- [ ] ✅ Sector classification accurate
- [ ] ✅ Quality scores >90 for all active stocks

---

## 🚀 Production Deployment

Once all checkboxes are checked:

```bash
# 1. Setup production database
createdb trading_system_prod

# 2. Run migrations
python scripts/setup_stock_data_pipeline.py --prod

# 3. Backfill production data
python -m src.data_pipeline.daily_price_scheduler \
  --backfill 2 --prod

# 4. Start scheduler as service
systemctl start stock-data-scheduler
systemctl enable stock-data-scheduler

# 5. Start API with Gunicorn
gunicorn src.api.main_complete:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --daemon

# 6. Build and deploy frontend
cd apps/web_dashboard/frontend
npm run build
# Deploy dist/ to nginx/Apache

# 7. Setup monitoring
# - Application logs: /var/log/trading-system/
# - Metrics: Prometheus/Grafana
# - Alerts: PagerDuty/Slack
```

---

## 📞 Support

If any checklist item fails:

1. Check logs: `tail -f logs/app.log`
2. Review error messages
3. Consult documentation:
   - `COMPLETE_DATA_FLOW_GUIDE.md`
   - `README_STOCK_DATA_PIPELINE.md`
   - `DATA_PIPELINE_CHEATSHEET.md`
4. Run diagnostic scripts:
   ```bash
   python scripts/diagnose_data_pipeline.py
   python scripts/test_api_endpoints.py
   ```

---

**Last Updated:** January 2025
**Status:** ✅ Ready for Production
