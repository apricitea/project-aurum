# Project Aurum

**Indonesian Quantitative Trading System** - Professional-grade trading platform optimized for the Indonesian Stock Exchange (IDX) with ensemble machine learning, real-time alerting, and comprehensive risk management.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Production Ready](https://img.shields.io/badge/Production-Ready-brightgreen.svg)](https://github.com/yourusername/project-aurum)

## 🚀 Quick Start

```bash
# Clone and start
git clone https://github.com/yourusername/project-aurum.git
cd project-aurum
docker-compose up -d

# Access
# API: http://localhost:8000
# Dashboard: http://localhost:3000
```

## 📚 Documentation

**Complete documentation is in [`docs/`](./docs/README.md)**

- 🎓 **[Getting Started](./docs/tutorials/getting-started.md)** - Your first setup
- 🔧 **[Developer Guide](./docs/how-to-guides/development/)** - Development workflow
- 🚀 **[Deployment](./docs/how-to-guides/deployment/)** - Production deployment
- 📖 **[API Reference](./docs/reference/api/)** - Complete API docs
- 💡 **[Architecture](./docs/reference/architecture/)** - System design

## ⚡ Key Features

- **🤖 Advanced ML Ensemble** - Multi-model trading signals for IDX
- **📊 Real-time Dashboard** - React TypeScript frontend
- **🛡️ Risk Management** - Comprehensive portfolio protection
- **📱 Multi-channel Alerts** - Email, Telegram, SMS notifications
- **🇮🇩 Indonesian Optimized** - Built specifically for IDX market

## 🏗️ Project Structure

```
project-aurum/
├── 📁 src/                           # 🔧 Source Code (Domain-Driven Design)
│   ├── domains/                      # Business domains (bounded contexts)
│   │   ├── trading/                  # 📈 Core trading logic & signals
│   │   │   ├── core/                 # Entities, value objects, domain services
│   │   │   ├── application/          # Use cases & application services
│   │   │   ├── infrastructure/       # ML models, external adapters
│   │   │   └── interfaces/           # API contracts & event handlers
│   │   ├── market_data/              # 📊 IDX data processing & feeds
│   │   ├── risk_management/          # 🛡️ Portfolio risk controls
│   │   ├── user_management/          # 👤 Authentication & users
│   │   └── analytics/                # 📈 Backtesting & performance
│   ├── shared/                       # Shared infrastructure
│   │   ├── database/                 # Database connections & schemas
│   │   ├── messaging/                # Event bus & messaging
│   │   ├── external_apis/            # Third-party integrations
│   │   └── monitoring/               # Observability & metrics
│   └── api/                          # FastAPI application entry
│       ├── main.py                   # Application factory
│       ├── dependencies.py           # Dependency injection
│       └── routers/                  # API route handlers
├── 📁 apps/                          # 🎨 Frontend Applications
│   └── web_dashboard/                # React TypeScript dashboard
│       ├── frontend/src/components/  # UI components
│       ├── frontend/src/pages/       # Page components
│       ├── frontend/src/store/       # State management
│       └── frontend/src/types/       # TypeScript definitions
├── 📁 docs/                          # 📚 Documentation (Diátaxis Framework)
│   ├── tutorials/                    # 🎓 Learning-oriented guides
│   ├── how-to-guides/                # 🔧 Problem-solving guides
│   │   ├── deployment/               # Docker, K8s, production
│   │   ├── development/              # Dev setup, testing, debugging
│   │   ├── trading/                  # Strategy creation, backtesting
│   │   └── compliance/               # Indonesian regulations
│   ├── reference/                    # 📖 Information-oriented docs
│   │   ├── api/                      # API documentation
│   │   ├── architecture/             # System architecture
│   │   ├── configuration/            # Environment setup
│   │   └── market-data/              # Data sources & formats
│   ├── explanation/                  # 💡 Understanding-oriented
│   ├── user-guides/                  # 👥 User-focused docs
│   ├── operations/                   # 🔧 DevOps & maintenance
│   └── project-meta/                 # 📋 Changelog, roadmap
├── 📁 infrastructure/                # 🚀 Infrastructure as Code
│   ├── docker/                       # 🐳 Container configurations
│   │   ├── docker-compose.yml        # Development setup
│   │   ├── docker-compose.prod.yml   # Production deployment
│   │   ├── docker-compose.staging.yml # Staging environment
│   │   └── Dockerfile                # Container build
│   ├── k8s/                          # ☸️ Kubernetes manifests
│   ├── terraform/                    # 🏗️ Cloud infrastructure
│   └── monitoring/                   # 📊 Prometheus, Grafana configs
├── 📁 tools/                         # 🛠️ Development Tools
│   ├── ci_cd/                        # 🔄 CI/CD configurations
│   ├── scripts/                      # 📜 Automation scripts
│   ├── linting/                      # ✅ Code quality configs
│   ├── security/                     # 🔒 Security scanning
│   ├── testing/                      # 🧪 Test utilities
│   └── utilities/                    # 🔧 Helper scripts
├── 🐳 docker-compose.yml             # Quick development setup
├── 🐳 Dockerfile                     # Container build file
├── 🐍 main.py                        # Application entry point
├── ⚙️ pyproject.toml                 # Project configuration
├── 📦 requirements.txt               # Python dependencies
└── 📄 README.md                      # This file
```

### 📍 **Where to Find/Put Files**

| **Looking for...** | **Go to...** | **Example** |
|-------------------|-------------|-------------|
| 🔧 **Trading Logic** | `src/domains/trading/` | Signal generation, ML models |
| 📊 **Data Processing** | `src/domains/market_data/` | IDX feeds, data validation |
| 🛡️ **Risk Controls** | `src/domains/risk_management/` | Position limits, drawdown rules |
| 🌐 **API Endpoints** | `src/api/routers/` | REST API routes |
| 🎨 **Frontend Code** | `apps/web_dashboard/frontend/src/` | React components, pages |
| 📚 **Documentation** | `docs/` | Guides, references, tutorials |
| 🐳 **Deployment** | `infrastructure/docker/` | Production configs |
| 🔧 **Dev Tools** | `tools/` | Scripts, linting, testing |
| ⚙️ **Configuration** | Root + `.env` | Environment variables |

## 🎯 Indonesian Market Focus

- **IDX Integration** - Real-time Indonesian Stock Exchange data
- **LQ45 Optimization** - Focus on most liquid Indonesian stocks
- **WIB Timezone** - Perfect for Indonesian trading hours
- **OJK Compliance** - Indonesian regulatory requirements
- **IDR Currency** - Native Indonesian Rupiah support

## 📊 Performance Targets

| Metric | Target | Status |
|--------|--------|--------|
| Annual Return | 15-25% | ✅ Backtested |
| Sharpe Ratio | 1.2-1.8 | ✅ Validated |
| Max Drawdown | <15% | ✅ Risk-managed |
| Signal Latency | <1 minute | ✅ Real-time |

## 💻 Development

```bash
# Backend
cd src && uvicorn api.main:app --reload

# Frontend
cd apps/web_dashboard && npm run dev

# Tests
pytest src/
```

## 🤝 Contributing

See [Contributing Guide](./docs/how-to-guides/development/contributing-code.md)

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

**🚀 Ready to start?** → [Getting Started Guide](./docs/tutorials/getting-started.md)