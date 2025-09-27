# Getting Started with Project Aurum

> **Complete tutorial for setting up your first Project Aurum instance and generating your first trading signals for the Indonesian Stock Exchange (IDX).**

## Prerequisites

Before starting, ensure you have:

- **Python 3.9+** installed
- **Node.js 18+** for the frontend
- **Docker & Docker Compose** for containerized deployment
- **8GB+ RAM** and **4+ CPU cores** recommended
- **Git** for version control

## Quick Setup (5 minutes)

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/project-aurum.git
cd project-aurum
```

### 2. Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit with your configuration
nano .env
```

Key environment variables to configure:
```bash
# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/trading_system

# API Keys (get from providers)
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key
YAHOO_FINANCE_API_KEY=optional_but_recommended

# Security
SECRET_KEY=your-super-secret-key-here
JWT_SECRET_KEY=another-secret-for-jwt

# Alerts
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
SMTP_SERVER=smtp.gmail.com
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
```

### 3. Start the System

```bash
# Start all services
docker-compose up -d

# Check service health
curl http://localhost:8000/health
```

### 4. Initialize the Database

```bash
# Run database migrations
docker-compose exec api python -m alembic upgrade head

# Seed with Indonesian market data
docker-compose exec api python scripts/seed_lq45_stocks.py
```

### 5. Create Your First User

```bash
# Access the API container
docker-compose exec api python

# Create admin user
from src.api.auth import create_user
user = create_user(
    username="admin",
    email="admin@example.com",
    password="secure_password",
    role="admin"
)
print(f"User created: {user.username}")
```

## Verification

### Test API Endpoints

```bash
# Health check
curl http://localhost:8000/health

# Get market data
curl http://localhost:8000/api/v1/market/stocks

# Generate test signal
curl http://localhost:8000/api/v1/signals/generate/BBCA
```

### Access the Dashboard

1. Open http://localhost:3000 in your browser
2. Login with your created credentials
3. Navigate to the Dashboard tab
4. You should see Indonesian market data loading

## Next Steps

🎯 **Ready to dive deeper?**

1. **[Generate Your First Trading Signal](./your-first-trading-signal.md)** - Learn how the ML models create trading recommendations
2. **[Understanding the Dashboard](../user-guides/dashboard-overview.md)** - Navigate the user interface
3. **[Setting Up Alerts](../user-guides/alert-configuration.md)** - Configure notifications for your trading signals

## Common Issues

### Port Conflicts
If port 8000 or 3000 are in use:
```bash
# Check which process is using the port
netstat -tulpn | grep :8000

# Kill the process or change ports in docker-compose.yml
```

### Database Connection Issues
```bash
# Check PostgreSQL logs
docker-compose logs postgres

# Restart database
docker-compose restart postgres
```

### Permission Issues
```bash
# Fix file permissions
sudo chown -R $USER:$USER .

# Reset Docker volumes if needed
docker-compose down -v
docker-compose up -d
```

## Development Mode

For development with hot reload:

```bash
# Backend development
cd src
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Frontend development
cd frontend
npm run dev
```

## System Architecture Overview

```mermaid
graph LR
    A[Market Data] --> B[Data Processing]
    B --> C[ML Models]
    C --> D[Signal Generation]
    D --> E[Alert System]
    E --> F[Dashboard]

    G[PostgreSQL] --> B
    H[Redis Cache] --> C
    I[FastAPI] --> F
```

Your Project Aurum instance is now ready for quantitative trading on the Indonesian Stock Exchange! 🚀

---

**Next Tutorial**: [Your First Trading Signal →](./your-first-trading-signal.md)

*Having issues? Check our [Debugging Guide](../how-to-guides/development/debugging-common-issues.md) or [join our community](https://github.com/yourusername/project-aurum/discussions).*