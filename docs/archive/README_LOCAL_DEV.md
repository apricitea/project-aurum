# 🚀 Local Development Setup Guide

This guide will help you set up the Project Aurum trading system on your local machine with a **real SQLite database** and **live data updates**.

## 📋 Prerequisites

- Python 3.10+ installed
- Node.js 18+ and npm installed
- `uv` or `pip` for Python package management

## 🎯 Quick Start (3 Steps)

### 1. Initialize the Database

Run the setup script to create and populate the SQLite database:

```bash
./scripts/setup_local_dev.sh
```

This script will:
- ✅ Create a `data/` directory
- ✅ Initialize SQLite database at `data/trading_system.db`
- ✅ Create database tables (users, alerts, signals, portfolio, etc.)
- ✅ Populate with sample trading data
- ✅ Create demo user accounts

### 2. Start the Backend Server

```bash
cd src
uv run uvicorn api.main_local:app --reload --host 0.0.0.0 --port 8000
```

Or with standard Python:

```bash
cd src
python -m uvicorn api.main_local:app --reload --host 0.0.0.0 --port 8000
```

The backend will be available at: **http://localhost:8000**

### 3. Start the Frontend

In a **new terminal**:

```bash
cd apps/web_dashboard/frontend
npm run dev
```

The frontend will be available at: **http://localhost:3000**

## 🔐 Demo Credentials

| Role   | Username | Password   |
|--------|----------|------------|
| Admin  | `admin`  | `admin123` |
| Trader | `trader` | `trader123` |

## 📊 What You Get

After setup, your database will contain:

### Sample Trading Signals (5)
- **BBCA.JK** - BUY signal (Banking sector)
- **BBRI.JK** - HOLD signal (Banking sector)
- **TLKM.JK** - SELL signal (Telecommunications)
- **ASII.JK** - STRONG_BUY signal (Consumer Goods)
- **UNVR.JK** - BUY signal (Consumer Goods)

### Sample Portfolio (3 positions)
- 10,000 shares of BBCA.JK at Rp 8,500
- 15,000 shares of BBRI.JK at Rp 4,400
- 8,000 shares of ASII.JK at Rp 5,100

### Sample Alerts (3)
- Price target reached for BBCA
- Portfolio concentration risk warning
- New signal generation notification

## 🔄 Data Updates

Unlike the mock backend (`main_simple.py`), this setup uses a **real database**:

- ✅ Data persists between restarts
- ✅ Changes are saved to the database
- ✅ You can add/edit/delete records
- ✅ All CRUD operations work properly

## 🛠️ Useful Commands

### Reset Database
```bash
rm data/trading_system.db
python scripts/init_database.py
```

### View Database
```bash
sqlite3 data/trading_system.db
```

### Check Database Tables
```sql
.tables
SELECT * FROM users;
SELECT * FROM trading_signals;
SELECT * FROM portfolio;
SELECT * FROM alerts;
```

### API Documentation
Visit **http://localhost:8000/docs** for interactive API documentation (Swagger UI)

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│  Frontend (React + TypeScript)          │
│  http://localhost:3000                  │
└────────────┬────────────────────────────┘
             │
             │ HTTP/REST API
             │
┌────────────▼────────────────────────────┐
│  Backend (FastAPI + Python)             │
│  http://localhost:8000                  │
│                                         │
│  - main_local.py (Dev server)           │
│  - Real authentication                   │
│  - SQLAlchemy ORM                       │
└────────────┬────────────────────────────┘
             │
             │ SQL
             │
┌────────────▼────────────────────────────┐
│  SQLite Database                        │
│  data/trading_system.db                 │
│                                         │
│  Tables:                                │
│  - users                                │
│  - trading_signals                      │
│  - portfolio                            │
│  - alerts                               │
│  - market_data                          │
│  - risk_alerts                          │
└─────────────────────────────────────────┘
```

## 🔍 Key Differences from Mock Backend

| Feature | Mock (main_simple.py) | Real (main_local.py) |
|---------|----------------------|----------------------|
| Database | None (hardcoded data) | SQLite |
| Data Persistence | ❌ No | ✅ Yes |
| User Authentication | Fake check | Real bcrypt + JWT |
| Data Updates | ❌ Not saved | ✅ Saved to DB |
| CRUD Operations | ❌ Fake | ✅ Real |
| Portfolio Tracking | Static | Dynamic |

## 🐛 Troubleshooting

### Database locked error
If you see "database is locked":
```bash
# Stop all running backend processes
pkill -f uvicorn

# Then restart
cd src && uv run uvicorn api.main_local:app --reload
```

### Permission denied on scripts
```bash
chmod +x scripts/setup_local_dev.sh
chmod +x scripts/init_database.py
```

### Module not found errors
```bash
# Reinstall dependencies
uv sync
# or
pip install -r requirements.txt
```

## 🚀 Production vs Development

For **production deployment** with PostgreSQL:
- Use `api/main.py` instead of `api/main_local.py`
- Configure PostgreSQL connection in `.env`
- Run migrations with Alembic
- Set up Redis for caching
- Configure proper authentication

For **local development** (what we just set up):
- Use `api/main_local.py` ✅ (current setup)
- SQLite database (simpler, no external dependencies)
- Auto-reload enabled
- Debug mode enabled

## 📚 Next Steps

1. Explore the API at http://localhost:8000/docs
2. Log in to the dashboard at http://localhost:3000
3. Try adding new trading signals
4. Modify portfolio positions
5. Create custom alerts

Happy trading! 🎯📈
