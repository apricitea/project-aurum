# Database Setup Guide for Project Aurum

## 🎯 Database Configuration

Project Aurum supports both **PostgreSQL** (production) and **SQLite** (development) databases.

---

## 🚀 Quick Start (Development)

For development, the project is **pre-configured to use SQLite** out of the box:

```bash
# SQLite is already configured in .env
DB_URL=sqlite:///data/trading_system.db

# Just start the backend - no database setup needed
./scripts/start-backend.sh
```

The SQLite database file is automatically created at `data/trading_system.db`.

---

## ⚙️ Database Options

### 1️⃣ SQLite (Development - Recommended)
- ✅ **Zero setup required**
- ✅ **Works out of the box**
- ✅ **No external dependencies**
- ✅ **Fast for development**

### 2️⃣ PostgreSQL (Production)
- ✅ **Better performance for large datasets**
- ✅ **Concurrent connections**
- ✅ **Advanced features**
- ❌ **Requires setup and configuration**

---

## 🛠️ SQLite Setup (Default)

The project comes with SQLite pre-configured:

### Configuration in `.env`:
```env
# Database Configuration - SQLite is already set up
DB_URL=sqlite:///data/trading_system.db
```

### Verify SQLite is working:
```bash
# Check database connection
uv run python -c "from src.api.config import settings; print('Database:', settings.get_database_url())"

# Should output: Database: sqlite:///data/trading_system.db
```

### Database file location:
```
project-aurum/
└── data/
    └── trading_system.db  ← SQLite database file (auto-created)
```

---

## 🗄️ PostgreSQL Setup (Optional/Production)

### Install PostgreSQL:
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install postgresql postgresql-contrib

# macOS (with Homebrew)
brew install postgresql
brew services start postgresql

# Windows
# Download from: https://postgresql.org/download/windows/
```

### Create Database:
```bash
# Switch to postgres user
sudo -u postgres psql

# In PostgreSQL shell:
CREATE DATABASE trading_system;
CREATE USER trading_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE trading_system TO trading_user;
\q
```

### Update `.env` for PostgreSQL:
```env
# Uncomment and configure PostgreSQL settings
# DB_URL=postgresql://trading_user:your_secure_password@localhost:5432/trading_system
DB_HOST=localhost
DB_PORT=5432
DB_NAME=trading_system
DB_USER=trading_user
DB_PASSWORD=your_secure_password
```

---

## 🔄 Switching Between Databases

### To use SQLite (Development):
```env
DB_URL=sqlite:///data/trading_system.db
```

### To use PostgreSQL (Production):
```env
DB_URL=postgresql://username:password@localhost:5432/trading_system
```

**Note**: The application automatically detects the database type from the connection URL.

---

## 🛠️ Database Management

### Reset Database (Start Fresh):
```bash
# For SQLite - just delete the file
rm data/trading_system.db

# For PostgreSQL - recreate tables
uv run python -c "
from src.api.database import DatabaseManager
import asyncio

async def reset():
    db = DatabaseManager()
    await db.initialize()
    await db.create_tables()

asyncio.run(reset())
print('Database reset complete')
"
```

### Check Database Status:
```bash
# Test connection
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","timestamp":"...","service":"alert-system","version":"1.0.0"}
```

---

## 🔍 Troubleshooting

### Issue: "Database configuration is incomplete"
**Solution**: This is normal for development with SQLite. The app continues with default settings.

### Issue: "password authentication failed for user postgres"
**Solution**: The app is configured to use SQLite for development. PostgreSQL authentication errors don't affect SQLite operation.

### Issue: Redis connection errors
**Solution**: Redis is optional for development. The app works without Redis, just with reduced functionality.

### Issue: Can't connect to database
**Solution**: Check your `.env` file:
```bash
# Verify database URL is set
grep DB_URL .env

# Should show: DB_URL=sqlite:///data/trading_system.db
```

---

## 📁 Database Files

When using SQLite, these files are created:

```
project-aurum/
├── data/
│   └── trading_system.db          ← Main SQLite database
├── models/                        ← ML model files (created as needed)
└── logs/                          ← Application logs
```

---

## 🚀 Ready to Start

With SQLite configured (the default), you can start the application immediately:

```bash
# Backend
./scripts/start-backend.sh

# Frontend (in another terminal)
./scripts/frontend-dev.sh dev
```

**No database setup required!** 🎉

---

## 📖 More Information

- **API Documentation**: http://localhost:8000/docs (once backend is running)
- **Frontend Dashboard**: http://localhost:3000 (once frontend is running)
- **Main Documentation**: `docs/README.md`
- **Development Guide**: `docs/how-to-guides/development/`