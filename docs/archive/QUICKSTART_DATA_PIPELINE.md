# Quick Start Guide - Stock Data Pipeline

Get your daily stock price data pipeline running in 5 minutes!

## Prerequisites

```bash
# Install dependencies (if not already installed)
pip install yfinance pandas sqlalchemy schedule pytz
```

## Step 1: Setup Database (1 minute)

```bash
# Run the setup script to create tables and seed stock data
python scripts/setup_stock_data_pipeline.py
```

**Expected output:**
```
Creating database tables...
✓ Database tables created successfully
Seeding stock master data...
✓ Stock master data seeded: 40 added, 0 updated
  Total stocks: 40
  LQ45 stocks: 25

Verifying setup...
✓ Stock Master: 40 total, 40 active, 25 LQ45
```

## Step 2: Backfill Historical Data (2-5 minutes)

```bash
# Fetch 2 years of historical data for all stocks
python -m src.data_pipeline.daily_price_scheduler --backfill 2
```

**Expected output:**
```
Backfilling 2 years of data from 2023-01-01 to 2025-01-01
Fetching BBCA (BBCA.JK)...
✓ BBCA: 504 records saved, quality: 98.5%
Fetching BBRI (BBRI.JK)...
✓ BBRI: 504 records saved, quality: 99.1%
...
Job completed: 20,160 inserted, 0 updated, 0 failed
```

## Step 3: Start Daily Scheduler (1 minute)

```bash
# Start the automated daily refresh
python -m src.data_pipeline.daily_price_scheduler
```

**Output:**
```
Starting Daily Price Scheduler
Scheduled run time: 17:30 Asia/Jakarta
Scheduler started. Press Ctrl+C to stop.
Next run: 2025-01-05 17:30:00
```

**That's it!** 🎉 Your data pipeline is now running and will automatically fetch daily stock prices.

---

## Quick Test

Verify data is loading correctly:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.api.database_extensions import DailyStockPrice, StockMaster

# Connect to database
engine = create_engine("sqlite:///data/trading_system.db")
Session = sessionmaker(bind=engine)
session = Session()

# Get latest price for BBCA
latest = session.query(DailyStockPrice).filter(
    DailyStockPrice.stock_code == "BBCA"
).order_by(DailyStockPrice.date.desc()).first()

print(f"BBCA Latest Price: Rp {latest.close_price:,.0f}")
print(f"Date: {latest.date}")
print(f"Change: {latest.price_change_percent:.2f}%")

# Count total records
total = session.query(DailyStockPrice).count()
print(f"\nTotal price records: {total:,}")

# Get all active stocks
stocks = session.query(StockMaster).filter(StockMaster.is_active == True).count()
print(f"Active stocks: {stocks}")
```

---

## Common Commands

### Run manual refresh (test mode)
```bash
python -m src.data_pipeline.daily_price_scheduler --run-once
```

### Refresh specific stocks only
```bash
python -m src.data_pipeline.daily_price_scheduler --run-once --stocks BBCA BBRI TLKM
```

### Backfill more historical data
```bash
# Backfill 5 years
python -m src.data_pipeline.daily_price_scheduler --backfill 5

# Backfill specific stocks
python -m src.data_pipeline.daily_price_scheduler --backfill 3 --stocks GOTO ASII
```

### Change scheduled time
```bash
# Run at 6:00 PM instead of default 5:30 PM
python -m src.data_pipeline.daily_price_scheduler --time 18:00
```

---

## Troubleshooting

### Issue: "No module named 'src'"
```bash
# Make sure you're in the project root directory
cd /path/to/project-aurum

# Or add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:/path/to/project-aurum"
```

### Issue: "No such table: stock_master"
```bash
# Re-run setup script
python scripts/setup_stock_data_pipeline.py
```

### Issue: API errors or no data returned
- Check internet connection
- Verify stock symbols are correct in `stock_master` table
- Yahoo Finance may have rate limits (retry after a few minutes)

---

## Next Steps

1. **Explore the data:**
   - See `README_STOCK_DATA_PIPELINE.md` for query examples
   - Build analytics dashboards
   - Run backtests on historical data

2. **Customize:**
   - Add more stocks to `stock_master`
   - Adjust scheduled run time
   - Configure data quality thresholds

3. **Production deployment:**
   - Run as systemd service (Linux)
   - Set up monitoring and alerts
   - Configure database backups

4. **Integration:**
   - Use data in your trading signals
   - Feed into ML models
   - Power your analytics dashboard

---

## Resources

- **Full Documentation:** `README_STOCK_DATA_PIPELINE.md`
- **Database Schema:** `src/api/database_extensions.py`
- **Data Fetcher:** `src/data_pipeline/daily_price_fetcher.py`
- **Scheduler:** `src/data_pipeline/daily_price_scheduler.py`

---

**Happy Trading! 📈**
