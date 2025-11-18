# Stock Data Pipeline - Quick Reference

One-page reference for common operations and commands.

---

## 🚀 Setup (One-Time)

```bash
# 1. Create tables and seed stock data
python scripts/setup_stock_data_pipeline.py

# 2. Backfill 2 years of historical data
python -m src.data_pipeline.daily_price_scheduler --backfill 2

# 3. Start daily scheduler
python -m src.data_pipeline.daily_price_scheduler
```

---

## 📋 Common Commands

### Scheduler Operations
```bash
# Run daily refresh once (test mode)
python -m src.data_pipeline.daily_price_scheduler --run-once

# Backfill historical data
python -m src.data_pipeline.daily_price_scheduler --backfill 5  # 5 years

# Refresh specific stocks
python -m src.data_pipeline.daily_price_scheduler --run-once --stocks BBCA BBRI TLKM

# Custom schedule time
python -m src.data_pipeline.daily_price_scheduler --time 18:00 --timezone Asia/Jakarta
```

### Python API
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.data_pipeline.daily_price_fetcher import DailyPriceFetcher

engine = create_engine("sqlite:///data/trading_system.db")
Session = sessionmaker(bind=engine)
session = Session()
fetcher = DailyPriceFetcher(session)

# Fetch today's prices
results, job_id = fetcher.fetch_daily_prices(backfill_days=1)

# Backfill specific stocks
results, job_id = fetcher.fetch_daily_prices(
    stock_codes=["BBCA", "BBRI"],
    backfill_days=30
)

# Data quality report
report = fetcher.get_data_quality_report(days=30)
```

---

## 🔍 Common Queries

### Get Latest Prices
```python
from src.api.database_extensions import DailyStockPrice, StockMaster

# Single stock latest
latest = session.query(DailyStockPrice).filter(
    DailyStockPrice.stock_code == "BBCA"
).order_by(DailyStockPrice.date.desc()).first()

print(f"{latest.stock_code}: Rp {latest.close_price:,.0f}")
print(f"Change: {latest.price_change_percent:.2f}%")
```

### Get Price History
```python
from datetime import date, timedelta

# Last 30 days for BBCA
history = session.query(DailyStockPrice).filter(
    DailyStockPrice.stock_code == "BBCA",
    DailyStockPrice.date >= date.today() - timedelta(days=30)
).order_by(DailyStockPrice.date.desc()).all()

for price in history:
    print(f"{price.date}: {price.close_price}")
```

### Cross-Sectional Queries
```python
# All stocks for a specific date
target_date = date.today()
all_stocks = session.query(DailyStockPrice).filter(
    DailyStockPrice.date == target_date
).all()

# Top gainers
gainers = session.query(DailyStockPrice).filter(
    DailyStockPrice.date == target_date
).order_by(DailyStockPrice.price_change_percent.desc()).limit(10).all()

for stock in gainers:
    print(f"{stock.stock_code}: +{stock.price_change_percent:.2f}%")
```

### Aggregate Statistics
```python
from sqlalchemy import func

# Calculate stats for last 30 days
stats = session.query(
    func.min(DailyStockPrice.low_price).label('min'),
    func.max(DailyStockPrice.high_price).label('max'),
    func.avg(DailyStockPrice.close_price).label('avg'),
    func.stddev(DailyStockPrice.price_change_percent).label('volatility')
).filter(
    DailyStockPrice.stock_code == "BBCA",
    DailyStockPrice.date >= date.today() - timedelta(days=30)
).first()

print(f"30-Day Stats: Min={stats.min}, Max={stats.max}, Avg={stats.avg:.2f}")
```

### Join with Stock Master
```python
# Get prices with company names
results = session.query(
    StockMaster.company_name,
    StockMaster.sector,
    DailyStockPrice.close_price,
    DailyStockPrice.volume
).join(
    DailyStockPrice,
    StockMaster.stock_code == DailyStockPrice.stock_code
).filter(
    DailyStockPrice.date == date.today()
).all()

for name, sector, price, volume in results:
    print(f"{name} ({sector}): Rp {price:,.0f}, Vol: {volume:,.0f}")
```

---

## 📊 Monitoring

### Check Job Logs
```python
from src.api.database_extensions import DataRefreshLog

# Last 10 jobs
recent_jobs = session.query(DataRefreshLog).order_by(
    DataRefreshLog.started_at.desc()
).limit(10).all()

for job in recent_jobs:
    print(f"{job.started_at}: {job.status} - {job.records_processed} records")
    if job.error_message:
        print(f"  Error: {job.error_message}")
```

### Data Quality Check
```python
# Stocks with quality issues
low_quality = session.query(StockMaster).filter(
    StockMaster.data_quality_score < 90
).all()

for stock in low_quality:
    print(f"{stock.stock_code}: {stock.data_quality_score:.1f}%")
```

### Count Records
```python
# Total records in database
total = session.query(DailyStockPrice).count()
print(f"Total price records: {total:,}")

# Records by stock
from sqlalchemy import func

by_stock = session.query(
    DailyStockPrice.stock_code,
    func.count(DailyStockPrice.id).label('count')
).group_by(DailyStockPrice.stock_code).all()

for code, count in by_stock:
    print(f"{code}: {count} records")
```

---

## 🛠️ Stock Management

### Add New Stock
```python
from src.api.database_extensions import StockMaster

new_stock = StockMaster(
    stock_code="ACES",
    yahoo_symbol="ACES.JK",
    company_name="Ace Hardware Indonesia Tbk",
    sector="Retail",
    industry="Home Improvement",
    is_lq45=False,
    market_cap_category="Mid",
    is_active=True
)

session.add(new_stock)
session.commit()

# Backfill data for new stock
fetcher.backfill_historical_data(stock_codes=["ACES"], years=2)
```

### Deactivate Stock
```python
stock = session.query(StockMaster).filter(
    StockMaster.stock_code == "OLDSTOCK"
).first()

stock.is_active = False
stock.delisting_date = date.today()
session.commit()
```

### List All Active Stocks
```python
active = session.query(StockMaster).filter(
    StockMaster.is_active == True
).order_by(StockMaster.stock_code).all()

for stock in active:
    print(f"{stock.stock_code}: {stock.company_name} ({stock.sector})")
```

---

## 🔧 Troubleshooting

### Database Connection
```python
# Test connection
from sqlalchemy import create_engine

engine = create_engine("sqlite:///data/trading_system.db")
try:
    connection = engine.connect()
    print("✓ Database connection successful")
    connection.close()
except Exception as e:
    print(f"✗ Connection failed: {e}")
```

### Verify Table Exists
```python
from sqlalchemy import inspect

inspector = inspect(engine)
tables = inspector.get_table_names()
print("Tables:", tables)

# Check specific table
if 'daily_stock_prices' in tables:
    print("✓ daily_stock_prices table exists")
```

### Check API Access
```python
import yfinance as yf

# Test Yahoo Finance access
ticker = yf.Ticker("BBCA.JK")
hist = ticker.history(period="1d")

if not hist.empty:
    print("✓ Yahoo Finance API accessible")
    print(hist)
else:
    print("✗ No data returned from Yahoo Finance")
```

---

## 📁 Important File Locations

```
project-aurum/
├── data/
│   └── trading_system.db              # SQLite database
├── scripts/
│   └── setup_stock_data_pipeline.py   # Setup script
├── src/
│   ├── api/
│   │   └── database_extensions.py     # Database schema
│   └── data_pipeline/
│       ├── daily_price_fetcher.py     # Data fetcher
│       └── daily_price_scheduler.py   # Scheduler
└── docs/
    ├── README_STOCK_DATA_PIPELINE.md  # Full documentation
    ├── QUICKSTART_DATA_PIPELINE.md    # Quick start
    └── DATA_PIPELINE_CHEATSHEET.md    # This file
```

---

## 🔑 Database Schema Quick Reference

### Tables
- `stock_master` - Stock metadata (40+ stocks)
- `daily_stock_prices` - Daily OHLCV data
- `data_refresh_logs` - Job execution logs
- `stock_fundamentals` - Financial metrics
- `data_quality_metrics` - Quality tracking

### Key Fields

**daily_stock_prices:**
- `stock_code`, `date` - Primary identifiers
- `open_price`, `high_price`, `low_price`, `close_price` - OHLC
- `volume`, `vwap`, `turnover_value` - Volume metrics
- `price_change`, `price_change_percent` - Changes
- `data_quality` - Quality flag

**stock_master:**
- `stock_code` - IDX ticker
- `yahoo_symbol` - Yahoo Finance symbol
- `company_name`, `sector`, `industry` - Metadata
- `is_lq45`, `is_active` - Status flags
- `data_quality_score` - Overall quality (0-100)

---

## ⚡ Performance Tips

### Optimize Queries
```python
# Use indexes - always filter by stock_code and/or date
session.query(DailyStockPrice).filter(
    DailyStockPrice.stock_code == "BBCA",
    DailyStockPrice.date >= start_date
).all()

# Use limit for large result sets
.limit(100)

# Use specific columns instead of *
session.query(
    DailyStockPrice.date,
    DailyStockPrice.close_price
).filter(...)
```

### Batch Operations
```python
# Bad: Individual commits
for stock_code in stock_codes:
    # fetch and save
    session.commit()  # DON'T DO THIS

# Good: Batch commit
for stock_code in stock_codes:
    # fetch and save
session.commit()  # Single commit at end
```

---

## 📞 Getting Help

1. **Documentation:** `README_STOCK_DATA_PIPELINE.md`
2. **Quick Start:** `QUICKSTART_DATA_PIPELINE.md`
3. **Summary:** `DATA_PIPELINE_SUMMARY.md`
4. **Source Code:** Comments in `.py` files

---

**Last Updated:** January 2025
