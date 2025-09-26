# Project Aurum - Claude Code Project Context

> 🤖 Auto-generated project analysis on 2025-09-22
> 📝 This file helps Claude Code understand your project across sessions

## 📋 Project Overview

**Project Type:** Indonesian Quantitative Trading System
**Technology Stack:** Python FastAPI + React TypeScript + PostgreSQL + Redis
**Primary Purpose:** AI-powered daily trading signals for Indonesian Stock Exchange (IDX)
**Package Manager:** pip (Python) + npm (Node.js)

### Key Business Domains
- **Quantitative Trading**: ML-powered buy/sell/hold signals for IDX stocks
- **Risk Management**: Portfolio risk monitoring and position sizing
- **Market Analytics**: Real-time Indonesian market data processing and analysis

## 🏗️ Architecture & Structure

### Directory Organization
```
project-aurum/
├── src/                     # Main Python source code
│   ├── api/                 # FastAPI backend services
│   └── data_pipeline/       # Data ingestion and processing
├── frontend/                # React TypeScript dashboard
├── tests/                   # Comprehensive test suite
├── docs/                    # Extensive documentation
├── scripts/                 # Automation and utility scripts
├── monitoring/              # Prometheus/Grafana configs
├── database/                # SQL schemas and optimizations
├── ml/                      # Machine learning models
└── sql/                     # Database initialization scripts
```

### Key Components
- **API Backend** (`src/api/main.py`): FastAPI application with async endpoints
- **Frontend Dashboard** (`frontend/src/`): React TypeScript with real-time charts
- **ML Engine** (`signal_generator.py`, `model_ensemble.py`): Ensemble ML models
- **Risk Monitor** (`src/api/risk_monitor.py`): Real-time portfolio risk management
- **Alert System** (`src/api/alert_engine.py`): Multi-channel notification system

## 🗄️ Data Architecture

### Databases
- **PostgreSQL**: Primary transactional database for user data, positions, alerts
  - Key tables: users, portfolios, signals, alerts, market_data
  - Access patterns: OLTP for user operations, analytical queries for reporting
- **Redis**: High-performance caching and session storage
  - Caching strategy: Market data, user sessions, computed indicators

### Data Sources
- **IDX Market Data**: Primary source for Indonesian stock prices and volume
- **Yahoo Finance**: Secondary data source for price validation and historical data
- **Alpha Vantage**: Fundamental data and economic indicators
- **Bank Indonesia**: Economic indicators and currency data

### Data Flow
```
IDX/Yahoo Finance → Data Gateway → Kafka → Feature Engineering → ML Models → Signals → API → Dashboard
```

## 🔧 Development Environment

### Prerequisites
```bash
# Python 3.9+, Node.js 18+, Docker & Docker Compose
# 8GB+ RAM, 4+ CPU cores recommended
```

### Common Tasks
```bash
# Start development environment
docker-compose up -d

# Backend development
cd src && uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Frontend development
cd frontend && npm run dev

# Run tests
pytest tests/ -v --cov=src

# Database operations
docker-compose exec postgres psql -U postgres -d trading_system

# Generate signals
python signal_generator.py
```

## 📦 Dependencies & Integrations

### Core Dependencies
**Backend (Python):**
- FastAPI 0.104.1 - High-performance async web framework
- pandas 2.1.3, numpy 1.25.2 - Data processing
- scikit-learn 1.3.2, xgboost 2.0.1 - Machine learning
- asyncpg 0.29.0, redis 5.0.1 - Database connectivity
- python-jose 3.3.0, passlib 1.7.4 - Authentication

**Frontend (TypeScript):**
- React 18.2.0 - UI framework
- TypeScript 5.1.6 - Type safety
- Vite 4.4.8 - Build tool
- Zustand 4.5.7 - State management
- Chart.js 4.3.3 - Data visualization

### External Services
- **IDX Market Data**: Real-time Indonesian stock market feed
- **Email/SMS/Telegram**: Multi-channel alert notifications
- **Prometheus/Grafana**: System monitoring and dashboards

### APIs
- **Authentication API**: JWT-based auth with refresh tokens
- **Signals API**: Daily trading recommendations with confidence scores
- **Portfolio API**: Position tracking and P&L calculations
- **Risk API**: Real-time risk monitoring and alerts

## 🛡️ Security & Compliance

### Data Security
- JWT authentication with role-based access control (Admin/Trader)
- Password hashing with bcrypt
- API rate limiting and CORS protection
- Environment-based configuration management

### Access Controls
- Database: Connection pooling with secure credentials
- APIs: Bearer token authentication for all protected endpoints
- Role permissions: Admin (full access), Trader (read-only + signals)

## 📊 Coding Conventions

### Python Style
- **Formatter**: Not specified (recommend black)
- **Linting**: Configured for flake8, mypy for type checking
- **Type Checking**: Type hints throughout codebase
- **Async/Await**: Extensive use for database and API operations

### SQL Conventions
- **NEVER use DELETE/DROP/TRUNCATE** - Use soft deletion with UPDATE
- **ALWAYS use WHERE TRUE pattern** for analytical queries
- **ALWAYS use LIMIT 10** for data sampling
- **MANDATORY notifications** before UPDATE/ALTER operations

### Git Workflow
- **Branch Strategy**: Feature branches with main branch
- **Commit Convention**: Descriptive commit messages
- **Automated**: Pre-commit hooks configured with .pre-commit-config.yaml

## 🎯 Current Focus Areas

### Active Development
- Production-ready quantitative trading system for Indonesian market
- Real-time signal generation with ensemble ML models
- Comprehensive risk management and portfolio monitoring

### Technical Debt
- Monitoring system needs frontend integration
- Some configuration could be more environment-specific
- Test coverage could be expanded for edge cases

### Planned Improvements
- Enhanced ML model performance with drift detection
- Mobile application for alerts and monitoring
- Advanced portfolio optimization algorithms

## ⚠️ Important Constraints

### Performance Requirements
- Sub-200ms API response times during market hours
- Real-time WebSocket updates for price changes
- Handle 50+ concurrent users simultaneously

### Business Rules
- Focus on LQ45 stocks (45 most liquid Indonesian stocks)
- Maximum 5% position size per stock, 25% per sector
- Trading hours: 09:00-15:49 WIB (Western Indonesian Time)
- T+2 settlement for Indonesian market compliance

### Compliance Requirements
- OJK (Otoritas Jasa Keuangan) regulatory compliance
- Indonesian Personal Data Protection (UU PDP) compliance
- Risk disclosure for all investment recommendations

## 🔍 Troubleshooting

### Common Issues
- **Database Connection**: Check PostgreSQL container health and credentials
- **Redis Cache**: Verify Redis service and connection parameters
- **Market Data**: Validate API keys for external data sources

### Debug Commands
```bash
# Check service health
curl http://localhost:8000/health

# View logs
docker-compose logs -f api

# Database status
docker-compose exec postgres pg_isready

# Redis connectivity
docker-compose exec redis redis-cli ping
```

## 📈 Metrics & Monitoring

### Key Metrics
- **Trading Performance**: Daily P&L, Sharpe ratio, win rate
- **System Performance**: API latency, database query times
- **Risk Metrics**: Portfolio volatility, maximum drawdown

### Monitoring Tools
- **Prometheus**: Metrics collection and alerting
- **Grafana**: Real-time dashboards and visualization
- **ELK Stack**: Centralized logging and analysis

---

## 🤖 Claude Code Instructions

### SQL Safety Rules
- **BLOCK**: All DELETE, DROP, TRUNCATE operations
- **NOTIFY**: Before any UPDATE or ALTER operations
- **REQUIRE**: WHERE clauses in all data operations (except sampling)
- **MANDATE**: LIMIT 10 for data exploration
- **ENFORCE**: WHERE TRUE pattern for analytical queries

### Agent Preferences
- **Primary Agents**: api-developer, ml-engineer, frontend-developer
- **Code Review**: Always use code-reviewer for Python/TypeScript changes
- **Documentation**: Auto-update with documentation-generator
- **Git Automation**: Use git-automator with safety checks

### Project-Specific Guidelines
- Focus on Indonesian market requirements (IDX, LQ45, WIB timezone)
- Maintain async/await patterns for database operations
- Ensure proper error handling and logging throughout
- Follow type safety practices in both Python and TypeScript
- Test Indonesian market data edge cases (market holidays, currency volatility)

### Development Workflow
- Always check service health before major changes
- Use feature branches for new development
- Run comprehensive tests before committing
- Update documentation for API changes
- Monitor performance impact of ML model updates

---

*Last Updated: 2025-09-26 | Next Analysis: 2025-10-03*